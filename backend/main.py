import base64
import hashlib
import hmac
import json
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
  sys.path.insert(0, str(BACKEND_DIR))

from config import generation_config, resolve_capabilities, settings
from auth import auth_enabled, create_session, is_admin_email, local_user, payment_enabled, require_entitled_user, require_user, scoped_chat_id, verify_google_credential, verify_session_token
from db import (
  ensure_user_entitlement,
  extend_user_entitlement,
  get_user_usage,
  increment_ingest_usage,
  increment_query_usage,
  init_db,
  record_payment_attempt,
)
from pipeline.generation import (
  deterministic_extraction_answer,
  deterministic_synthesis_answer,
  ollama_base_url,
  request_ollama,
  request_ollama_models,
  allowed_ollama_models,
  resolve_ollama_model,
)
from pipeline.ingestion import SUPPORTED_SUFFIXES, build_chunk_records, extract_text_segments, sanitize_filename
from models import (
  ChatRequest,
  ChatResponse,
  ClearDocumentsRequest,
  AuthResponse,
  AuthUser,
  GoogleAuthRequest,
  IngestedDocument,
  IngestResponse,
  PaymentOrderResponse,
  PaymentVerifyRequest,
  RetrievalResult,
  RetrieveRequest,
  RetrieveResponse,
)
from pipeline.retrieval import retrieve_context
from pipeline.retrieval import query_intent
from pipeline.retrieval import query_broadness_score
from pipeline.retrieval_v0 import retrieve_context as retrieve_context_v0
from pipeline.retrieval_v1 import retrieve_context as retrieve_context_v1
from pipeline.retrieval_v2 import retrieve_context as retrieve_context_v2
from pipeline.retrieval_v3 import retrieve_context as retrieve_context_v3
from pipeline.retrieval_v31 import retrieve_context as retrieve_context_v31
from storage import chat_dir, chunks_path, documents_path, load_json, save_json, uploads_dir


RAG_VERSIONS = {
  "v0": {
    "label": "V0 Similarity Toy",
    "description": "Token cosine similarity baseline for showing why toy RAG breaks down.",
    "retrieve_context": retrieve_context_v0,
  },
  "v1": {
    "label": "V1 Sparse Foundation",
    "description": "First BM25/hierarchical baseline.",
    "retrieve_context": retrieve_context_v1,
  },
  "v2": {
    "label": "V2 Routed Retrieval",
    "description": "Improved routing and extraction-aware behavior.",
    "retrieve_context": retrieve_context_v2,
  },
  "v3": {
    "label": "V3 Benchmark Baseline",
    "description": "Production-style synthesis/extraction benchmark baseline.",
    "retrieve_context": retrieve_context_v3,
  },
  "v3.1": {
    "label": "V3.1 Clean Baseline",
    "description": "Final clean baseline with evidence-first extraction and document-balanced context.",
    "retrieve_context": retrieve_context_v31,
  },
}


def normalize_rag_version(version: str | None) -> str:
  requested = (version or "v3.1").strip().lower()
  aliases = {
    "v31": "v3.1",
    "3.1": "v3.1",
    "3": "v3",
    "2": "v2",
    "1": "v1",
    "0": "v0",
  }
  return aliases.get(requested, requested if requested in RAG_VERSIONS else "v3.1")


def retrieve_with_version(
  version: str | None,
  query: str,
  chunks: list[dict],
  requested_top_k: int | None = None,
) -> tuple[list[dict], dict, str]:
  normalized = normalize_rag_version(version)
  retrieval_fn = RAG_VERSIONS[normalized]["retrieve_context"]
  results, stats = retrieval_fn(query, chunks, requested_top_k)
  stats = {
    **stats,
    "rag_version": normalized,
    "rag_version_label": RAG_VERSIONS[normalized]["label"],
  }
  return results, stats, normalized


app_settings = settings()
generation_slots = threading.BoundedSemaphore(app_settings["max_active_clients"])
app = FastAPI(
  title=app_settings["app_name"],
  docs_url=app_settings["docs_path"],
  openapi_url=app_settings["openapi_path"],
)
init_db()

app.add_middleware(
  CORSMiddleware,
  allow_origins=app_settings["cors_origins"] or ["http://localhost:5173"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

api = app_settings["api_prefix"]


def require_vram_capacity() -> None:
  required_gb = float(app_settings.get("vram_required_gb", 0) or 0)
  available_gb = float(app_settings.get("vram_available_gb", 0) or 0)
  if required_gb and available_gb < required_gb:
    raise HTTPException(
      status_code=503,
      detail=f"Model unavailable: requires {required_gb:g}GB VRAM, configured available VRAM is {available_gb:g}GB.",
    )


def require_ollama_model_installed(model: str) -> None:
  try:
    installed_models = request_ollama_models()
  except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
    return
  if installed_models and model not in installed_models:
    raise HTTPException(status_code=503, detail=f"Ollama model is not installed: {model}. Run `ollama pull {model}` on the server.")


class GenerationSlot:
  def __enter__(self):
    require_vram_capacity()
    if not generation_slots.acquire(blocking=False):
      raise HTTPException(status_code=429, detail="Model busy: one client is already using generation. Try again shortly.")
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    generation_slots.release()
    return False


@app.get(f"{api}/health")
def health() -> dict:
  return {
    "status": "ok",
    "service": app_settings["app_name"],
    "environment": app_settings["app_env"],
  }


@app.get(f"{api}/config")
def config() -> dict:
  return {
    "config": app_settings["config"],
    "config_file": app_settings["config_file"],
    "runtime": {
      "jwt_secret_configured": app_settings["jwt_secret_configured"],
      "jwt_secret_generated": app_settings["jwt_secret_generated"],
    },
  }


@app.get(f"{api}/capabilities")
def capabilities() -> dict:
  return resolve_capabilities()


@app.get(f"{api}/models")
def models() -> dict:
  generation = generation_config()
  default_model = generation.get("default_model", "qwen3:4b-instruct")
  allowed_models = allowed_ollama_models()
  if allowed_models and default_model not in allowed_models:
    default_model = allowed_models[0]

  try:
    installed_models = request_ollama_models()
    ollama_models = [model for model in installed_models if not allowed_models or model in allowed_models]
    ollama_available = True
  except (OSError, urllib.error.URLError, TimeoutError):
    ollama_models = allowed_models
    ollama_available = False
  if allowed_models:
    ollama_models = [model for model in allowed_models if model in set(ollama_models)] or allowed_models

  return {
    "default_provider": generation.get("default_provider", "ollama"),
    "default_model": default_model,
    "providers": generation.get("providers", {}),
    "ollama": {
      "available": ollama_available,
      "base_url": ollama_base_url(),
      "models": ollama_models,
      "allowed_models": allowed_models,
    },
  }


@app.get(f"{api}/rag-versions")
def rag_versions() -> dict:
  return {
    "default": "v3.1",
    "versions": [
      {
        "id": version,
        "label": metadata["label"],
        "description": metadata["description"],
      }
      for version, metadata in RAG_VERSIONS.items()
    ],
  }


@app.post(f"{api}/auth/google", response_model=AuthResponse)
def google_auth(request: GoogleAuthRequest) -> AuthResponse:
  if not auth_enabled():
    return AuthResponse(token="", user=AuthUser(**local_user()))

  user = verify_google_credential(request.credential)
  entitlement = ensure_user_entitlement(
    user,
    is_admin_email(user.get("email", "")),
  )
  token = create_session(user, paid=entitlement["paid"], exp_override=entitlement["exp"])
  return AuthResponse(token=token, user=AuthUser(**verify_session_token(token)))


@app.get(f"{api}/auth/me", response_model=AuthUser)
def auth_me(user: dict = Depends(require_user)) -> AuthUser:
  return AuthUser(**user)


@app.get(f"{api}/usage/me")
def usage_me(user: dict = Depends(require_user)) -> dict:
  usage = get_user_usage(user["sub"])
  return {
    "user": usage or {
      "sub": user["sub"],
      "email": user.get("email", ""),
      "is_admin": bool(user.get("is_admin")),
      "entitled_until": int(user.get("exp", 0)),
      "query_count": 0,
      "ingest_count": 0,
      "uploaded_chunk_count": 0,
      "payment_count": 0,
      "total_payments_paise": 0,
    }
  }


@app.post(f"{api}/payment/order", response_model=PaymentOrderResponse)
def create_payment_order(user: dict = Depends(require_user)) -> PaymentOrderResponse:
  app_config = settings()
  if not payment_enabled():
    raise HTTPException(status_code=404, detail="Payments are not enabled.")
  if user.get("is_admin"):
    raise HTTPException(status_code=400, detail="Admin users do not need payment.")

  payload = {
    "amount": app_config["razorpay_amount_paise"],
    "currency": app_config["razorpay_currency"],
    "receipt": f"cf_{hashlib.sha1(user['sub'].encode('utf-8')).hexdigest()[:10]}_{int(time.time())}",
    "notes": {
      "email": user.get("email", ""),
      "duration_seconds": str(app_config["auth_session_seconds"]),
    },
  }
  record_payment_attempt(user["sub"], user.get("email", ""), app_config["razorpay_amount_paise"], app_config["razorpay_currency"])
  credentials = f"{app_config['razorpay_key_id']}:{app_config['razorpay_key_secret']}".encode("utf-8")
  request = urllib.request.Request(
    "https://api.razorpay.com/v1/orders",
    data=json.dumps(payload).encode("utf-8"),
    headers={
      "Authorization": f"Basic {base64.b64encode(credentials).decode('ascii')}",
      "Content-Type": "application/json",
    },
    method="POST",
  )

  try:
    with urllib.request.urlopen(request, timeout=20) as response:
      order = json.loads(response.read().decode("utf-8"))
  except urllib.error.HTTPError as error:
    detail = error.read().decode("utf-8", errors="replace")
    raise HTTPException(status_code=502, detail=f"Razorpay order failed: {detail}") from error
  except (OSError, TimeoutError, json.JSONDecodeError) as error:
    raise HTTPException(status_code=502, detail=f"Razorpay order failed: {error}") from error

  return PaymentOrderResponse(
    key_id=app_config["razorpay_key_id"],
    order_id=order["id"],
    amount=order["amount"],
    currency=order["currency"],
  )


@app.post(f"{api}/payment/verify", response_model=AuthResponse)
def verify_payment(request: PaymentVerifyRequest, user: dict = Depends(require_user)) -> AuthResponse:
  app_config = settings()
  if not payment_enabled():
    raise HTTPException(status_code=404, detail="Payments are not enabled.")
  if user.get("is_admin"):
    token = create_session(user, paid=True)
    return AuthResponse(token=token, user=AuthUser(**verify_session_token(token)))

  signed_payload = f"{request.razorpay_order_id}|{request.razorpay_payment_id}".encode("utf-8")
  expected = hmac.new(
    app_config["razorpay_key_secret"].encode("utf-8"),
    signed_payload,
    hashlib.sha256,
  ).hexdigest()
  if not hmac.compare_digest(expected, request.razorpay_signature):
    raise HTTPException(status_code=401, detail="Invalid Razorpay signature.")

  new_expiry = extend_user_entitlement(
    user["sub"],
    user.get("email", ""),
    app_config["razorpay_amount_paise"],
    app_config["auth_session_seconds"],
  )
  token = create_session(user, paid=True, exp_override=new_expiry)
  return AuthResponse(token=token, user=AuthUser(**verify_session_token(token)))


@app.get(f"{api}/documents")
def list_documents(chat_id: str = "default", user: dict = Depends(require_entitled_user)) -> dict:
  chat_id = scoped_chat_id(chat_id, user)
  documents = load_json(documents_path(chat_id), [])
  chunks = load_json(chunks_path(chat_id), [])

  return {
    "chat_id": chat_id,
    "documents": documents,
    "total_documents": len(documents),
    "total_chunks": len(chunks),
  }


@app.post(f"{api}/documents/clear")
def clear_documents(request: ClearDocumentsRequest, user: dict = Depends(require_entitled_user)) -> dict:
  chat_id = scoped_chat_id(request.chat_id, user)
  target_dir = chat_dir(chat_id)
  if target_dir.exists():
    shutil.rmtree(target_dir)

  return {
    "chat_id": chat_id,
    "documents": [],
    "total_documents": 0,
    "total_chunks": 0,
  }


@app.post(f"{api}/ingest", response_model=IngestResponse)
async def ingest(
  chat_id: str = Form("default"),
  files: list[UploadFile] = File(...),
  user: dict = Depends(require_entitled_user),
) -> IngestResponse:
  chat_id = scoped_chat_id(chat_id, user)
  if not files:
    raise HTTPException(status_code=400, detail="No files uploaded.")

  documents = load_json(documents_path(chat_id), [])
  max_upload_files = int(app_settings.get("max_upload_files", 5) or 5)
  if len(files) > max_upload_files:
    raise HTTPException(status_code=400, detail=f"Upload limit exceeded: maximum {max_upload_files} files per upload.")
  if len(documents) + len(files) > max_upload_files:
    remaining = max(0, max_upload_files - len(documents))
    raise HTTPException(status_code=400, detail=f"Document limit exceeded: this workspace allows {max_upload_files} files. Remaining slots: {remaining}.")

  upload_root = uploads_dir(chat_id)
  upload_root.mkdir(parents=True, exist_ok=True)

  chunks = load_json(chunks_path(chat_id), [])
  ingested_documents = []

  for upload in files:
    original_filename = upload.filename or "document.txt"
    safe_filename = sanitize_filename(original_filename)
    suffix = Path(safe_filename).suffix.lower()

    if suffix not in SUPPORTED_SUFFIXES:
      raise HTTPException(status_code=400, detail=f"Unsupported file type: {original_filename}")

    upload_order = len(documents)
    stored_filename = f"{upload_order:02d}_{safe_filename}"
    stored_path = upload_root / stored_filename
    raw_bytes = await upload.read()
    stored_path.write_bytes(raw_bytes)

    document_id = f"doc_{upload_order:04d}"
    segments = extract_text_segments(raw_bytes, suffix, original_filename)
    document_chunks = build_chunk_records(
      document_id=document_id,
      original_filename=original_filename,
      stored_filename=stored_filename,
      segments=segments,
    )
    chunks.extend(document_chunks)

    document = {
      "id": document_id,
      "original_filename": original_filename,
      "stored_filename": stored_filename,
      "upload_order": upload_order,
      "chunk_count": len(document_chunks),
    }
    documents.append(document)
    ingested_documents.append(IngestedDocument(**document))

  save_json(documents_path(chat_id), documents)
  save_json(chunks_path(chat_id), chunks)
  increment_ingest_usage(user["sub"], user.get("email", ""), len(ingested_documents), sum(document.chunk_count for document in ingested_documents))

  return IngestResponse(
    chat_id=chat_id,
    documents=ingested_documents,
    total_documents=len(documents),
    total_chunks=len(chunks),
  )


@app.post(f"{api}/retrieve", response_model=RetrieveResponse)
def retrieve(request: RetrieveRequest, user: dict = Depends(require_entitled_user)) -> RetrieveResponse:
  start = time.perf_counter()
  chat_id = scoped_chat_id(request.chat_id, user)
  chunks = load_json(chunks_path(chat_id), [])
  max_top_k = min(settings()["config"].get("limits", {}).get("max_top_k", 10), 12)
  requested_top_k = max(1, min(request.top_k, max_top_k)) if request.top_k is not None else None
  results, stats, normalized_version = retrieve_with_version(
    request.rag_version,
    request.query,
    chunks,
    requested_top_k,
  )

  return RetrieveResponse(
    query=request.query,
    mode=stats.get("mode", normalized_version),
    results=[RetrievalResult(**result) for result in results],
    total_chunks=len(chunks),
    latency_ms=int((time.perf_counter() - start) * 1000),
  )


@app.post(f"{api}/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user: dict | None = Depends(require_entitled_user)) -> ChatResponse:
  start = time.perf_counter()
  retrieval_start = time.perf_counter()
  generation = generation_config()
  enabled_providers = {
    name for name, enabled in generation.get("providers", {}).items() if enabled
  }
  default_provider = generation.get("default_provider", "ollama")
  provider = default_provider if request.provider == "auto" else request.provider
  if provider not in enabled_providers:
    raise HTTPException(status_code=400, detail=f"Provider is disabled: {provider}")
  model = request.model or generation.get("default_model", "qwen3:4b-instruct")
  fallback_used = False
  reasoning_summary = ""
  retrieval_context = []
  retrieval_stats = {}
  total_chunks = 0
  retrieval_latency_ms = 0
  chat_id = scoped_chat_id(request.chat_id, user)

  if request.use_retrieval:
    chunks = load_json(chunks_path(chat_id), [])
    fallback_chat_id = request.chat_id
    if not chunks and request.chat_id != "default" and query_broadness_score(request.message) > 0:
      default_chunks = load_json(chunks_path("default"), [])
      if default_chunks:
        chunks = default_chunks
        fallback_chat_id = "default"
    total_chunks = len(chunks)
    retrieval_context, retrieval_stats, normalized_version = retrieve_with_version(
      request.rag_version,
      request.message,
      chunks,
    )
    if fallback_chat_id != request.chat_id:
      retrieval_stats = {**retrieval_stats, "fallback_chat_id": fallback_chat_id}
    retrieval_latency_ms = int((time.perf_counter() - retrieval_start) * 1000)

  force_ollama = request.provider == "ollama"

  if request.use_retrieval and not force_ollama and query_intent(request.message) == "extraction":
    answer = deterministic_extraction_answer(request.message, retrieval_context)
    reasoning_summary = (
      "- Use deterministic extraction mode because the query asks for a table/list of technical items.\n"
      "- Build the answer directly from extracted evidence terms in retrieved chunks."
    )
    provider = "extractor"
    model = "deterministic"
  elif request.use_retrieval and not force_ollama and query_intent(request.message) == "synthesis":
    answer = deterministic_synthesis_answer(request.message, retrieval_context)
    reasoning_summary = (
      "- Use deterministic synthesis mode because the query asks across uploaded documents.\n"
      "- Build a per-document evidence matrix before comparing or sequencing concepts."
    )
    provider = "synthesis"
    model = "deterministic"
  else:
    try:
      model = resolve_ollama_model(model)
      require_ollama_model_installed(model)
      with GenerationSlot():
        reasoning_summary, answer = request_ollama(
          request.message,
          request.messages,
          retrieval_context,
          load_json(documents_path(chat_id), []),
          model,
        )
      provider = "ollama"
    except urllib.error.HTTPError as error:
      error_body = error.read().decode("utf-8", errors="replace")
      raise HTTPException(status_code=503, detail=f"Ollama request failed: HTTP {error.code} {error.reason}. {error_body}") from error
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
      raise HTTPException(status_code=503, detail=f"Ollama request failed: {error}") from error

  latency_ms = int((time.perf_counter() - start) * 1000)
  if isinstance(user, dict) and user.get("sub"):
    increment_query_usage(user["sub"], user.get("email", ""), normalize_rag_version(request.rag_version), provider)
  return ChatResponse(
    answer=answer,
    provider=provider,
    model=model,
    latency_ms=latency_ms,
    fallback_used=fallback_used,
    reasoning_summary=reasoning_summary,
    citations=[RetrievalResult(**result) for result in retrieval_context],
    retrieval={
      "mode": retrieval_stats.get("mode", "bm25_hierarchical"),
      "rag_version": retrieval_stats.get("rag_version", normalize_rag_version(request.rag_version)),
      "rag_version_label": retrieval_stats.get("rag_version_label", ""),
      "latency_ms": retrieval_latency_ms,
      "selected_count": retrieval_stats.get("selected_count", len(retrieval_context)),
      "top_k": retrieval_stats.get("top_k", len(retrieval_context)),
      "intent": retrieval_stats.get("intent", "general"),
      "candidate_k": retrieval_stats.get("candidate_k", 0),
      "candidate_count": retrieval_stats.get("candidate_count", 0),
      "total_chunks": total_chunks,
      "fallback_chat_id": retrieval_stats.get("fallback_chat_id", ""),
    },
  )


if __name__ == "__main__":
  import uvicorn

  uvicorn.run(app, host="127.0.0.1", port=8000)
