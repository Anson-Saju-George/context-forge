import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
  sys.path.insert(0, str(BACKEND_DIR))

from benchmarks.ultimate_data import QUESTION_GROUPS, VERSION_BRIEFINGS
from main import chat
from models import ChatMessage, ChatRequest
from pipeline.generation import allowed_ollama_models, request_ollama_models
from pipeline.ingestion import SUPPORTED_SUFFIXES, build_chunk_records, extract_text_segments, sanitize_filename
from storage import chat_dir, chunks_path, documents_path, save_json, uploads_dir


VERSIONS = ["v0", "v1", "v2", "v3", "v3.1"]


class Tee:
  def __init__(self, *streams):
    self.streams = streams

  def write(self, text: str) -> int:
    for stream in self.streams:
      try:
        stream.write(text)
      except UnicodeEncodeError:
        safe_text = text.encode(stream.encoding or "utf-8", errors="replace").decode(stream.encoding or "utf-8")
        stream.write(safe_text)
      stream.flush()
    return len(text)

  def flush(self) -> None:
    for stream in self.streams:
      stream.flush()


def start_log() -> tuple[Path, object, object, object]:
  log_dir = BACKEND_DIR / "reports" / "ultimate_runs"
  log_dir.mkdir(parents=True, exist_ok=True)
  timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
  log_path = log_dir / f"ultimate_run_{timestamp}.txt"
  log_file = log_path.open("w", encoding="utf-8")
  original_stdout = sys.stdout
  original_stderr = sys.stderr
  sys.stdout = Tee(original_stdout, log_file)
  sys.stderr = Tee(original_stderr, log_file)
  return log_path, log_file, original_stdout, original_stderr


def ask(prompt: str, default: str) -> str:
  value = input(f"{prompt} [{default}]: ").strip()
  selected = value or default
  print(f"[selected] {prompt}: {selected}")
  return selected


def choose_versions() -> list[str]:
  print("\nVersions")
  print("1. all")
  for index, version in enumerate(VERSIONS, start=2):
    print(f"{index}. {version}")
  raw = ask("Choose versions: all, number, version, or comma-list", "all")
  if raw.lower() == "all":
    return VERSIONS

  selected = []
  for item in re.split(r"[,\s]+", raw):
    if not item:
      continue
    version = VERSIONS[int(item) - 2] if item.isdigit() and int(item) >= 2 else item
    if version not in VERSIONS:
      raise ValueError(f"Unknown version: {item}")
    if version not in selected:
      selected.append(version)
  return selected or VERSIONS


def choose_mode() -> str:
  print("\nQuestion groups")
  print("1. set   = first five questions")
  print("2. stack = separate sixth question only")
  print("3. all   = first five + sixth")
  raw = ask("Choose question group", "set").lower()
  return {"1": "set", "2": "stack", "3": "all"}.get(raw, raw if raw in QUESTION_GROUPS else "set")


def choose_answer_mode() -> str:
  print("\nAnswer mode")
  print("1. deterministic = benchmark synthesis/extraction path")
  print("2. ollama        = force Ollama model generation")
  raw = ask("Choose answer mode", "ollama").lower()
  return {"1": "auto", "2": "ollama", "deterministic": "auto"}.get(raw, raw if raw in {"auto", "ollama"} else "ollama")


def available_ollama_models() -> list[str]:
  allowed_models = allowed_ollama_models()
  try:
    installed_models = request_ollama_models()
  except Exception:
    installed_models = []

  if allowed_models and installed_models:
    models = [model for model in allowed_models if model in set(installed_models)]
    return models or allowed_models
  return allowed_models or installed_models


def choose_ollama_model() -> str | None:
  models = available_ollama_models()
  if not models:
    return ask("Ollama model, blank = backend default", "") or None

  print("\nOllama models")
  print("1. backend default")
  for index, model in enumerate(models, start=2):
    print(f"{index}. {model}")

  raw = ask("Choose Ollama model: number, model name, or blank", "1")
  if raw in {"", "1"}:
    return None
  if raw.isdigit():
    index = int(raw)
    if 2 <= index < 2 + len(models):
      return models[index - 2]
    raise ValueError(f"Unknown model option: {raw}")
  if raw not in models:
    raise ValueError(f"Unknown model: {raw}")
  return raw


def source_files(source_dir: Path) -> list[Path]:
  return sorted(
    path for path in source_dir.iterdir()
    if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
  )


def clean_original_name(filename: str) -> str:
  return re.sub(r"^\d{2}_", "", filename)


def reingest(source_dir: Path, chat_id: str) -> tuple[int, int]:
  target_dir = chat_dir(chat_id)
  if target_dir.exists():
    shutil.rmtree(target_dir)

  upload_root = uploads_dir(chat_id)
  upload_root.mkdir(parents=True, exist_ok=True)
  documents, chunks = [], []

  for upload_order, source_path in enumerate(source_files(source_dir)):
    original_filename = clean_original_name(source_path.name)
    safe_filename = sanitize_filename(original_filename)
    stored_filename = f"{upload_order:02d}_{safe_filename}"
    raw_bytes = source_path.read_bytes()
    (upload_root / stored_filename).write_bytes(raw_bytes)

    document_id = f"doc_{upload_order:04d}"
    document_chunks = build_chunk_records(
      document_id=document_id,
      original_filename=original_filename,
      stored_filename=stored_filename,
      segments=extract_text_segments(raw_bytes, Path(safe_filename).suffix.lower(), original_filename),
    )
    chunks.extend(document_chunks)
    documents.append({
      "id": document_id,
      "original_filename": original_filename,
      "stored_filename": stored_filename,
      "upload_order": upload_order,
      "chunk_count": len(document_chunks),
    })

  if not documents:
    raise RuntimeError(f"No supported source documents found in {source_dir}")

  save_json(documents_path(chat_id), documents)
  save_json(chunks_path(chat_id), chunks)
  return len(documents), len(chunks)


def print_list(title: str, values: list[str]) -> None:
  print(title)
  for value in values:
    print(f"- {value}")


def print_briefing(version: str) -> None:
  briefing = VERSION_BRIEFINGS[version]
  print("Version briefing")
  print(f"Label: {briefing['label']}")
  print(f"Purpose: {briefing['purpose']}")
  for key, title in [
    ("retrieval", "Retrieval algorithms / behavior:"),
    ("ranking", "Ranking algorithms / behavior:"),
    ("context", "Context algorithms / behavior:"),
    ("answering", "Answering / generation behavior:"),
    ("strengths", "Expected strengths:"),
    ("limits", "Known limits:"),
    ("files", "Implementation files:"),
  ]:
    print_list(title, briefing[key])


def print_sources(citations: list, max_sources: int) -> None:
  print("Sources" if citations else "Sources: none")
  for index, citation in enumerate(citations[:max_sources], start=1):
    rerank = f" rerank={citation.rerank_score}" if citation.rerank_score is not None else ""
    page = f" page={citation.page}" if citation.page else ""
    section = f" section={citation.section}" if citation.section else ""
    print(f"[{index}] {citation.source} score={citation.score}{rerank}{page}{section}")
    if citation.rerank_reasons:
      print(f"    {' | '.join(citation.rerank_reasons[:3])}")


def truncate(text: str, max_chars: int) -> str:
  clean = text.strip()
  if max_chars <= 0 or len(clean) <= max_chars:
    return clean
  return f"{clean[:max_chars].rstrip()}\n...[truncated at {max_chars} chars]"


def run_question(
  version: str,
  chat_id: str,
  name: str,
  prompt: str,
  provider: str,
  model: str | None,
  max_chars: int,
  max_sources: int,
) -> None:
  start = time.perf_counter()
  response = chat(ChatRequest(
    message=prompt.strip(),
    chat_id=chat_id,
    provider=provider,
    model=model,
    use_retrieval=True,
    rag_version=version,
    messages=[ChatMessage(role="user", content=prompt.strip())],
  ))
  wall_ms = int((time.perf_counter() - start) * 1000)

  print("\n" + "=" * 100)
  print(f"{version} / {name}")
  print("-" * 100)
  print("Question")
  print(prompt.strip())
  print("\nStats")
  retrieval_stats = {
    f"retrieval_{key}" if key == "latency_ms" else key: value
    for key, value in response.retrieval.items()
  }
  print({
    "provider": response.provider,
    "model": response.model,
    "backend_total_latency_ms": response.latency_ms,
    "runner_wall_ms": wall_ms,
    **retrieval_stats,
  })
  if response.reasoning_summary:
    print("\nReasoning")
    print(response.reasoning_summary.strip())
  print("\nAnswer")
  print(truncate(response.answer, max_chars))
  print()
  print_sources(response.citations, max_sources)


def main() -> None:
  log_path, log_file, original_stdout, original_stderr = start_log()
  try:
    print("ContextForge Ultimate Runner")
    print(f"log_file={log_path}")
    versions = choose_versions()
    mode = choose_mode()
    provider = choose_answer_mode()
    model = choose_ollama_model() if provider == "ollama" else None
    source_chat_id = ask("Source chat id", "default")
    chat_prefix = ask("Fresh chat prefix", "ultimate")
    max_chars = int(ask("Max answer chars, 0 = full", "0"))
    max_sources = int(ask("Max sources shown", "8"))
    source_dir = uploads_dir(source_chat_id)
    questions = QUESTION_GROUPS[mode]

    print(f"\nsource_dir={source_dir}")
    print(f"versions={', '.join(versions)}")
    print(f"mode={mode}")
    print(f"answer_provider={provider}")
    print(f"answer_model={model or 'backend default'}")
    print(f"questions={len(questions)} ({', '.join(name for name, _ in questions)})")

    for version in versions:
      chat_id = f"{chat_prefix}_{version.replace('.', '_')}"
      print("\n" + "#" * 100)
      print(f"VERSION {version}")
      print("#" * 100)
      print_briefing(version)
      print("\nReingesting corpus")
      print(f"chat_id={chat_id}")
      document_count, chunk_count = reingest(source_dir, chat_id)
      print(f"documents={document_count} chunks={chunk_count}")

      for name, prompt in questions:
        run_question(version, chat_id, name, prompt, provider, model, max_chars, max_sources)

    print(f"\nSaved terminal log: {log_path}")
  finally:
    sys.stdout.flush()
    sys.stderr.flush()
    sys.stdout = original_stdout
    sys.stderr = original_stderr
    log_file.close()


if __name__ == "__main__":
  main()
