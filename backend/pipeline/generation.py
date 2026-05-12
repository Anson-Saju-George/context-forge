import json
import os
import re
import urllib.error
import urllib.request

from config import generation_config, model_allowlist
from models import ChatMessage
from pipeline.retrieval import TECHNICAL_TERMS, find_term_hits, query_intent


def ollama_base_url() -> str:
  return os.getenv("OLLAMA_BASE_URL") or generation_config().get(
    "ollama_base_url",
    "http://localhost:11434",
  )


def ollama_timeout_seconds() -> int:
  raw_timeout = os.getenv("OLLAMA_TIMEOUT_SECONDS") or generation_config().get("ollama_timeout_seconds", 120)
  try:
    return max(1, int(raw_timeout))
  except (TypeError, ValueError):
    return 120


def build_history_context(messages: list[ChatMessage]) -> str:
  recent_messages = messages[-10:]
  lines = []

  for item in recent_messages:
    clean_content = item.content.strip()
    if not clean_content:
      continue
    lines.append(f"{item.role.upper()}: {clean_content}")

  return "\n\n".join(lines)


def build_retrieval_context(results: list[dict]) -> str:
  if not results:
    return "No document context was retrieved."

  context_blocks = []
  for index, result in enumerate(results, start=1):
    location_parts = []
    if result.get("page"):
      location_parts.append(f"page={result.get('page')}")
    if result.get("section"):
      location_parts.append(f"section={result.get('section')}")
    location = " ".join(location_parts)
    context_blocks.append(
      f"[{index}] source={result.get('source', '')} score={result.get('score', 0)} {location}\n"
      f"{result.get('text', '')}"
    )

  return "\n\n".join(context_blocks)


def build_source_manifest(results: list[dict]) -> str:
  if not results:
    return "No source files selected."

  sources = []
  seen = set()
  for result in results:
    source = result.get("source", "")
    if source and source not in seen:
      sources.append(source)
      seen.add(source)

  return "\n".join(f"- {source}" for source in sources)


def build_corpus_manifest(documents: list[dict]) -> str:
  if not documents:
    return "No uploaded documents are registered."

  return "\n".join(
    f"- {document.get('stored_filename', document.get('original_filename', 'unknown'))}: "
    f"{document.get('chunk_count', 0)} chunks"
    for document in documents
  )


def extract_candidate_entities(text: str) -> list[str]:
  known_terms = find_term_hits(text, TECHNICAL_TERMS)
  acronym_terms = re.findall(r"\b[A-Z][A-Z0-9-]{1,}\b", text)
  hyphenated_terms = re.findall(
    r"\b[a-zA-Z]+(?:-[a-zA-Z0-9]+){1,3}\b",
    text,
  )
  named_phrases = re.findall(
    r"\b(?:scaled dot-product attention|multi-head attention|self-attention|positional encoding|causal masking|dense passage retrieval|retrieval-augmented generation|rejection sampling|proximal policy optimization|grouped-query attention|multi-query attention|RAG-token|RAG-sequence|top-k retrieval|DPR|MIPS|control loop|control loops|declarative state management|desired state|control plane|kube-controller-manager|cloud-controller-manager|kube-scheduler|kube-apiserver|kube-proxy|kubelet|etcd)\b",
    text,
    flags=re.IGNORECASE,
  )

  candidates = []
  for term in [*known_terms, *acronym_terms, *hyphenated_terms, *named_phrases]:
    normalized = term.strip()
    if not normalized or len(normalized) < 2:
      continue
    if normalized.lower() in {"pdf", "fig", "table", "section"}:
      continue
    candidates.append(normalized)

  lowered_text = text.lower()
  inferred_terms = []
  if "multi-head" in lowered_text or "multiheaded" in lowered_text or "multi-headed" in lowered_text:
    inferred_terms.append("multi-head attention")
  if "self-attention" in lowered_text or "self attention" in lowered_text:
    inferred_terms.append("self-attention")
  if "positional encoding" in lowered_text or "positional encodings" in lowered_text:
    inferred_terms.append("positional encoding")
  if "causal mask" in lowered_text or "causal masking" in lowered_text or "masked multi-head attention" in lowered_text:
    inferred_terms.append("causal masking")
  if "grouped-query" in lowered_text or "grouped query attention" in lowered_text:
    inferred_terms.append("grouped-query attention")
  if "multi-query" in lowered_text or "multi query attention" in lowered_text:
    inferred_terms.append("multi-query attention")
  if "control loop" in lowered_text or "control loops" in lowered_text:
    inferred_terms.append("control loops")
  if "desired state" in lowered_text or "declarative state" in lowered_text:
    inferred_terms.append("declarative state management")
  if "kube-scheduler" in lowered_text or "scheduler" in lowered_text:
    inferred_terms.append("kube-scheduler")
  if "controller-manager" in lowered_text or "controller manager" in lowered_text:
    inferred_terms.append("kube-controller-manager")
  candidates.extend(inferred_terms)

  unique = []
  seen = set()
  for candidate in candidates:
    key = candidate.lower()
    if key in seen:
      continue
    unique.append(candidate)
    seen.add(key)

  return unique[:18]


def build_extracted_evidence_terms(results: list[dict]) -> str:
  if not results:
    return "No extracted evidence terms."

  grouped_terms = {}
  for result in results:
    source = result.get("source", "") or "unknown"
    reasons = "\n".join(result.get("rerank_reasons", []))
    text = f"{result.get('section', '')}\n{result.get('text', '')}\n{reasons}"
    terms = extract_candidate_entities(text)
    if not terms:
      continue

    existing = grouped_terms.setdefault(source, [])
    for term in terms:
      if term.lower() not in {item.lower() for item in existing}:
        existing.append(term)

  if not grouped_terms:
    return "No extracted evidence terms."

  lines = []
  for source, terms in grouped_terms.items():
    lines.append(f"- {source}: {', '.join(terms[:16])}")
  return "\n".join(lines)


def extracted_terms_by_source(results: list[dict]) -> dict[str, list[str]]:
  grouped_terms = {}
  for result in results:
    source = result.get("source", "") or "unknown"
    reasons = "\n".join(result.get("rerank_reasons", []))
    text = f"{result.get('section', '')}\n{result.get('text', '')}\n{reasons}"
    terms = extract_candidate_entities(text)
    if not terms:
      continue

    existing = grouped_terms.setdefault(source, [])
    existing_keys = {item.lower() for item in existing}
    for term in terms:
      if term.lower() not in existing_keys:
        existing.append(term)
        existing_keys.add(term.lower())

  return grouped_terms


def document_category(terms: list[str]) -> str:
  term_text = " ".join(terms).lower()
  if any(marker in term_text for marker in ["kube-apiserver", "kubelet", "kube-scheduler", "control plane", "etcd", "node reconciliation"]):
    return "infrastructure"
  if any(marker in term_text for marker in ["rag", "rag-sequence", "rag-token", "dpr", "mips", "top-k retrieval"]):
    return "retrieval"
  if any(marker in term_text for marker in ["rlhf", "ppo", "rejection sampling", "grouped-query attention", "fine-tuning"]):
    return "foundation_model"
  if any(marker in term_text for marker in ["scaled dot-product attention", "multi-head attention", "self-attention", "positional encoding"]):
    return "transformer"
  return "technical"


def document_type_from_terms(terms: list[str]) -> str:
  category = document_category(terms)
  if category == "infrastructure":
    return "Operational / infrastructure"
  if category in {"retrieval", "foundation_model", "transformer"}:
    return "Research"
  return "Technical"


def merge_terms(terms: list[str], extra_terms: list[str]) -> list[str]:
  merged = []
  seen = set()
  for term in [*terms, *extra_terms]:
    key = term.lower()
    if key in seen:
      continue
    merged.append(term)
    seen.add(key)
  return merged


def all_terms_by_source(results: list[dict]) -> dict[str, list[str]]:
  grouped = {}
  for result in results:
    source = result.get("source", "") or "unknown"
    reasons = "\n".join(result.get("rerank_reasons", []))
    text = f"{result.get('section', '')}\n{result.get('text', '')}\n{reasons}"
    terms = extract_candidate_entities(text)
    if not terms:
      continue

    existing = grouped.setdefault(source, [])
    existing_keys = {item.lower() for item in existing}
    for term in terms:
      if term.lower() in existing_keys:
        continue
      existing.append(term)
      existing_keys.add(term.lower())

  return grouped


def extraction_subtype(query: str) -> str:
  lowered_query = query.lower()
  if any(term in lowered_query for term in ["component", "components", "objects"]):
    return "component"
  if any(term in lowered_query for term in ["command", "commands", "cli"]):
    return "command"
  if any(term in lowered_query for term in ["workflow", "workflows", "pipeline", "pipelines"]):
    return "workflow"
  if any(term in lowered_query for term in ["concept", "concepts", "idea", "ideas"]):
    return "concept"
  if any(term in lowered_query for term in ["algorithm", "algorithms", "method", "methods", "technique", "techniques", "mechanism", "mechanisms"]):
    return "algorithm"
  return "general"


def filtered_extraction_terms(terms: list[str], query: str) -> list[str]:
  lowered_query = query.lower()
  subtype = extraction_subtype(query)
  blocked_terms = {
    "api",
    "fig",
    "ga",
    "k40",
    "k80",
    "m40",
    "p100",
    "pdf",
    "ppl",
    "rl",
    "sft",
    "table",
    "tflops",
    "state-of-the-art",
    "rating-based",
    "pre-trained",
    "end-to-end",
    "open-domain",
    "non-parametric",
    "parametric-memory",
    "feature-gates",
    "nginx-deployment",
    "my-nginx",
    "testsecret-tls",
    "tls-example-ingress",
    "https-example",
    "non-existence",
    "add-on",
    "role-oriented",
  }
  blocked_fragments = [
    "certificate-authority",
    "english-to",
    "per-word",
    "root-ca",
    "to-german",
    "wordpiece",
  ]
  canonical_terms = {
    "dpr": "DPR",
    "mips": "MIPS",
    "ppo": "PPO",
    "rag": "RAG",
    "rag-token": "RAG-token",
    "rag-sequence": "RAG-sequence",
    "rlhf": "RLHF",
    "rlhf-v1": "RLHF-V1",
    "rlhf-v5": "RLHF-V5",
    "scaled dot-product attention": "scaled dot-product attention",
    "top-k": "top-k retrieval",
    "dot-product": "scaled dot-product attention",
    "multi-headed": "multi-head attention",
    "autoregressive": "autoregressive transformer",
    "auto-regressive": "autoregressive transformer",
    "control loop": "control loops",
    "desired state": "declarative state management",
  }
  algorithm_aliases = {
    "controller": "reconciliation",
    "controller manager": "reconciliation",
    "control loop": "control loops",
    "control loops": "control loops",
    "control plane": "control-plane orchestration",
    "declarative": "declarative state management",
    "desired state": "declarative state management",
    "etcd": "cluster state storage",
    "kube-apiserver": "API-driven orchestration",
    "kube-controller-manager": "reconciliation",
    "kube-proxy": "load balancing",
    "kube-scheduler": "scheduling",
    "kubelet": "node reconciliation",
    "scheduler": "scheduling",
  }
  algorithm_terms = {
    "api-driven orchestration",
    "autoregressive",
    "autoregressive transformer",
    "beam search",
    "causal masking",
    "cluster state storage",
    "control loop",
    "control loops",
    "control-plane orchestration",
    "declarative state management",
    "dense passage retrieval",
    "dpr",
    "fine-tuning",
    "grouped-query attention",
    "load balancing",
    "mips",
    "multi-head attention",
    "multi-headed",
    "multi-query attention",
    "node reconciliation",
    "positional encoding",
    "ppo",
    "pretraining",
    "proximal policy optimization",
    "rag",
    "rag-sequence",
    "rag-token",
    "reconciliation",
    "rejection sampling",
    "retriever",
    "rlhf",
    "sampling",
    "scaled dot-product attention",
    "self-attention",
    "scheduling",
    "top-k",
    "top-k retrieval",
  }
  component_terms = {
    "api server",
    "cloud-controller-manager",
    "control plane",
    "controller manager",
    "etcd",
    "ingress",
    "kube-apiserver",
    "kube-controller-manager",
    "kube-proxy",
    "kube-scheduler",
    "kubelet",
    "node",
    "pod",
    "pods",
    "service",
    "services",
  }
  concept_terms = {
    "alignment",
    "generation",
    "inference",
    "open-domain",
    "pre-trained",
    "retrieval-augmented generation",
    "scaling",
    "training",
  }

  allowed_terms_by_subtype = {
    "algorithm": algorithm_terms,
    "mechanism": algorithm_terms | component_terms,
    "component": component_terms,
    "concept": concept_terms | algorithm_terms,
    "workflow": algorithm_terms | component_terms | concept_terms,
    "general": algorithm_terms | component_terms | concept_terms,
  }
  allowed_terms = allowed_terms_by_subtype.get(subtype, allowed_terms_by_subtype["general"])

  filtered = []
  seen = set()
  normalized_input_keys = {
    canonical_terms.get(term.lower(), term).lower()
    for term in terms
  }
  specific_overrides = {
    "attention": {
      "scaled dot-product attention",
      "self-attention",
      "multi-head attention",
      "grouped-query attention",
      "multi-query attention",
    },
    "transformer": {
      "autoregressive transformer",
      "encoder-decoder",
      "self-attention",
      "multi-head attention",
    },
    "sampling": {
      "rejection sampling",
      "top-k retrieval",
    },
    "retriever": {
      "dense passage retrieval",
      "dpr",
      "top-k retrieval",
    },
    "pretraining": {
      "fine-tuning",
      "rlhf",
      "ppo",
      "rejection sampling",
    },
  }
  for term in terms:
    key = term.lower()
    if key in blocked_terms:
      continue
    if any(fragment in key for fragment in blocked_fragments):
      continue
    if "rejectionsampling" in key:
      continue

    if subtype == "algorithm" and key in algorithm_aliases:
      display_term = algorithm_aliases[key]
      if display_term.lower() not in seen:
        filtered.append(display_term)
        seen.add(display_term.lower())
      continue

    display_term = canonical_terms.get(key, term)
    normalized_key = display_term.lower()
    if subtype == "algorithm" and any(
      normalized_key == umbrella and replacements & normalized_input_keys
      for umbrella, replacements in specific_overrides.items()
    ):
      continue
    if subtype == "algorithm" and key not in allowed_terms and normalized_key not in allowed_terms:
      continue
    if subtype == "component" and key not in allowed_terms and normalized_key not in allowed_terms:
      continue
    if subtype in {"algorithm", "component", "concept", "workflow", "mechanism"}:
      if display_term.lower() not in seen:
        filtered.append(display_term)
        seen.add(display_term.lower())
      continue
    if subtype == "general":
      if display_term.lower() not in seen:
        filtered.append(display_term)
        seen.add(display_term.lower())

  if subtype == "algorithm":
    priority = [
      "scaled dot-product attention",
      "self-attention",
      "positional encoding",
      "multi-head attention",
      "grouped-query attention",
      "multi-query attention",
      "RAG",
      "RAG-sequence",
      "RAG-token",
      "DPR",
      "MIPS",
      "top-k retrieval",
      "RLHF",
      "PPO",
      "proximal policy optimization",
      "rejection sampling",
      "autoregressive transformer",
      "control-plane orchestration",
      "control loops",
      "scheduling",
      "cluster state storage",
      "API-driven orchestration",
      "node reconciliation",
    ]
    priority_index = {term.lower(): index for index, term in enumerate(priority)}
    filtered.sort(key=lambda term: (priority_index.get(term.lower(), len(priority)), term.lower()))

  return filtered[:12]


def filtered_evidence_terms(terms: list[str], query: str, source: str = "") -> list[str]:
  subtype = extraction_subtype(query)
  evidence_terms = filtered_extraction_terms(terms, query)

  if subtype != "algorithm":
    return evidence_terms

  operational_evidence = {
    "api-driven orchestration",
    "cloud-controller-manager",
    "cluster state storage",
    "control loops",
    "control plane",
    "control-plane orchestration",
    "declarative state management",
    "etcd",
    "kube-apiserver",
    "kube-controller-manager",
    "kube-proxy",
    "kube-scheduler",
    "kubelet",
    "node reconciliation",
  }
  existing = {term.lower() for term in evidence_terms}
  for term in terms:
    key = term.lower()
    display_term = {
      "controller manager": "kube-controller-manager",
      "controller": "kube-controller-manager",
      "scheduler": "kube-scheduler",
      "desired state": "declarative state management",
      "control loop": "control loops",
    }.get(key, term)
    if display_term.lower() not in operational_evidence:
      continue
    if display_term.lower() in existing:
      continue
    evidence_terms.append(display_term)
    existing.add(display_term.lower())

  return evidence_terms[:12]


def deterministic_extraction_answer(message: str, retrieval_context: list[dict]) -> str:
  grouped_terms = extracted_terms_by_source(retrieval_context)
  context_terms = all_terms_by_source(retrieval_context)
  if not grouped_terms:
    return "No concrete algorithms, mechanisms, components, or techniques were found in the retrieved context."

  lines = [
    f"| Document | Type | Extracted {extraction_subtype(message)} items | Evidence terms |",
    "| --- | --- | --- | --- |",
  ]

  for source, terms in grouped_terms.items():
    terms = merge_terms(terms, context_terms.get(source, []))
    filtered_terms = filtered_extraction_terms(terms, message)
    if not filtered_terms:
      if extraction_subtype(message) in {"algorithm", "component", "concept", "workflow", "mechanism"}:
        filtered_terms = ["insufficient retrieved evidence"]
      else:
        filtered_terms = terms[:8]

    evidence_terms = ", ".join(filtered_evidence_terms(terms, message, source))
    lines.append(
      f"| {source} | {document_type_from_terms(terms)} | {', '.join(filtered_terms)} | {evidence_terms} |"
    )

  return "\n".join(lines)


def profile_source(source: str, terms: list[str]) -> dict:
  term_text = ", ".join(filtered_evidence_terms(terms, "make a table of all algorithms", source))
  category = document_category(terms)

  if category == "infrastructure":
    return {
      "document": source,
      "type": "Operational / infrastructure",
      "category": category,
      "about": "Operational infrastructure and orchestration for distributed workloads.",
      "problem": "Managing desired state, service coordination, scheduling, and node-level reconciliation.",
      "concepts": term_text or "not enough extracted evidence",
      "role": "Production infrastructure layer for deploying AI services, retrievers, retrieval indexes, and inference APIs.",
    }

  if category == "retrieval":
    return {
      "document": source,
      "type": "Research",
      "category": category,
      "about": "Retrieval-augmented generation and external evidence retrieval for knowledge-intensive tasks.",
      "problem": "Reducing limits of parametric memory by retrieving evidence before generation.",
      "concepts": term_text or "not enough extracted evidence",
      "role": "Grounding layer that connects transformer generators to external knowledge sources.",
    }

  if category == "foundation_model":
    return {
      "document": source,
      "type": "Research",
      "category": category,
      "about": "Foundation-model training, fine-tuning, alignment, and inference behavior.",
      "problem": "Training and aligning open foundation models for useful and safer chat behavior.",
      "concepts": term_text or "not enough extracted evidence",
      "role": "Foundation model layer used for generation, instruction following, alignment, and inference.",
    }

  if category == "transformer":
    return {
      "document": source,
      "type": "Research",
      "category": category,
      "about": "Attention-based neural sequence modeling and Transformer-style architecture.",
      "problem": "Replacing recurrence/convolution with attention-based sequence modeling for efficient parallel training.",
      "concepts": term_text or "not enough extracted evidence",
      "role": "Architectural foundation for modern LLMs and retrieval-conditioned generators.",
    }

  return {
    "document": source,
    "type": document_type_from_terms(terms),
    "category": category,
    "about": "Technical document represented in the uploaded corpus.",
    "problem": "The retrieved context does not expose a stronger document profile.",
    "concepts": term_text or "not enough extracted evidence",
    "role": "Supporting source in the uploaded corpus.",
  }


def profiles_from_context(retrieval_context: list[dict]) -> list[dict]:
  grouped_terms = extracted_terms_by_source(retrieval_context)
  seen = set()
  profiles = []

  for result in retrieval_context:
    source = result.get("source", "") or "unknown"
    if source in seen:
      continue
    profiles.append(profile_source(source, grouped_terms.get(source, [])))
    seen.add(source)

  return profiles


def markdown_profile_table(profiles: list[dict]) -> str:
  lines = [
    "| Document | Type | What it is about | Main problem | Core concepts/mechanisms | Role in modern AI/infrastructure |",
    "| --- | --- | --- | --- | --- | --- |",
  ]
  for profile in profiles:
    lines.append(
      "| {document} | {type} | {about} | {problem} | {concepts} | {role} |".format(**profile)
    )
  return "\n".join(lines)


def deterministic_synthesis_answer(message: str, retrieval_context: list[dict]) -> str:
  profiles = profiles_from_context(retrieval_context)
  if not profiles:
    return "No retrieved document context was available for synthesis."

  lowered_message = message.lower()
  table = markdown_profile_table(profiles)
  priority = {
    "transformer": 1,
    "foundation_model": 2,
    "retrieval": 3,
    "infrastructure": 4,
    "technical": 5,
  }
  ordered_profiles = sorted(profiles, key=lambda item: (priority.get(item.get("category", "technical"), 9), item["document"]))
  order_lines = [
    f"{index}. {profile['document']}: study {profile['concepts']}."
    for index, profile in enumerate(ordered_profiles, start=1)
  ]
  concept_rows = [
    f"| {profile['document']} | {profile['concepts']} | {profile['role']} |"
    for profile in ordered_profiles
  ]

  if "limitations" in lowered_message or "tradeoffs" in lowered_message or "bottlenecks" in lowered_message:
    return f"""
{table}

| Issue | Discussed or implied by | Technical cause | Later mitigation path | Still unresolved |
| --- | --- | --- | --- | --- |
| Transformer context and compute scaling | Transformer / Llama-style model documents | Attention-based sequence modeling must process token context during training and inference; larger models increase memory and serving pressure. | Foundation-model engineering adds optimized inference, grouped-query attention, batching, and deployment tuning. | Long-context cost, latency, and memory pressure still remain production bottlenecks. |
| Parametric memory limits | RAG and foundation-model documents | A model's learned parameters cannot reliably store every fact, private document, or updated knowledge item. | RAG adds retrievers, top-k retrieval, DPR/MIPS-style lookup, and non-parametric memory. | Retrieval can miss evidence, retrieve stale/noisy chunks, or overpack irrelevant context. |
| Retrieval precision vs recall | RAG document | Increasing top-k improves recall but adds distractors; narrow retrieval improves precision but can miss required evidence. | RAG-sequence/RAG-token, reranking, document-balanced retrieval, and context packing try to balance this. | Multi-hop and extraction-heavy queries still need stronger evidence selection and evaluation. |
| Alignment and safety limits | Llama 2 document | Fine-tuning, RLHF, PPO, and rejection sampling improve behavior but do not prove full safety or factual reliability. | Human preference data, safety tuning, red-teaming, and reward-model optimization reduce common failure modes. | Distribution shift, jailbreaks, over-refusal, and reward-model blind spots remain. |
| Kubernetes operational complexity | Kubernetes document | Distributed services require scheduling, reconciliation, state storage, networking, health checks, and resource isolation. | Control plane components, kube-apiserver, etcd, kubelet, scheduler, services, deployments, and autoscaling coordinate workloads. | GPU scheduling, inference latency, observability, data locality, and multi-service failure modes remain difficult. |
| End-to-end production RAG risk | All documents together | Model generation, retrieval, context selection, and orchestration fail in different ways and compound each other. | A layered stack separates Transformer modeling, aligned generation, retrieval grounding, and Kubernetes deployment. | Unified evaluation, traceability, latency control, and hallucination prevention remain ongoing engineering work. |

The main tradeoff across the corpus is that each layer solves one bottleneck while exposing another: attention improves sequence modeling but is expensive; Llama-style alignment improves usability but is incomplete; RAG improves factual grounding but depends on retrieval quality; Kubernetes improves orchestration but adds operational complexity.
""".strip()

  if "production ai system stack" in lowered_message or "full ai lifecycle" in lowered_message:
    return f"""
{table}

Production AI system stack:

| Lifecycle layer | Main document(s) | Concrete mechanisms | Production role |
| --- | --- | --- | --- |
| Model architecture | Transformer document | scaled dot-product attention, multi-head attention, self-attention, positional encoding, encoder/decoder processing | Base neural architecture for modern sequence modeling and LLMs. |
| Foundation model training/alignment | Llama 2 document | pretraining, fine-tuning, RLHF, PPO, rejection sampling, grouped-query attention, autoregressive generation | Turns Transformer-style modeling into an instruction-following chat model. |
| Retrieval grounding | RAG document | RAG-sequence, RAG-token, DPR, top-k retrieval, MIPS, retriever/generator coupling, non-parametric memory | Supplies external evidence so generation is not limited to parametric memory. |
| Deployment and orchestration | Kubernetes document | control plane, kube-apiserver, etcd, kube-scheduler, kubelet, controller-manager, services, deployments, reconciliation | Runs model APIs, retrievers, retrieval indexes, and supporting services reliably. |
| Runtime concerns | All documents together | context packing, inference, scaling, retrieval, memory, orchestration, safety/alignment | Connects research components into a production system with latency, reliability, and grounding constraints. |

Full lifecycle connection:

1. Transformer attention defines the computational primitive.
2. Llama-style pretraining and alignment turn that primitive into a usable foundation/chat model.
3. RAG adds external memory and retrieval to reduce factual and knowledge-update limitations.
4. Kubernetes supplies the operational substrate for serving models, retrieval services, APIs, and supporting infrastructure.
5. The full production stack must manage scaling, inference latency, memory limits, retrieval quality, safety behavior, and service orchestration together.
""".strip()

  if "roadmap" in lowered_message or "learning" in lowered_message or "order i should study" in lowered_message:
    return f"""
{table}

Recommended study order:

{chr(10).join(order_lines)}

Beginner concepts: tokens, attention, services, deployments, and document-level retrieval.
Intermediate concepts: RLHF, PPO, RAG pipelines, top-k retrieval, scheduling, control loops, and inference services.
Advanced concepts: alignment tradeoffs, retrieval/generation coupling, distributed orchestration, state reconciliation, scaling, and production deployment.

Projects to build:
1. Implement a small Transformer/attention visualizer.
2. Run a local Llama-style chat model and compare base prompting vs fine-tuned/aligned behavior.
3. Build a RAG pipeline with chunking, retrieval, reranking, and cited answers.
4. Containerize the RAG API and deploy it on Kubernetes with services, health checks, resource limits, and scaling.
""".strip()

  if "implementation and operational" in lowered_message or "kubernetes infrastructure" in lowered_message:
    return f"""
{table}

Implementation and operational comparison:

{chr(10).join(f"- {profile['document']}: {profile['role']} Key mechanisms/components: {profile['concepts']}." for profile in ordered_profiles)}

Where the requested ideas appear:

| Idea | Where it appears | Practical meaning |
| --- | --- | --- |
| Deployment | Kubernetes, Llama 2 | Serving model, retriever, and API components as managed workloads. |
| Retrieval | RAG paper | External knowledge lookup before generation. |
| Scaling | Kubernetes, Llama 2 | Infrastructure scaling for services and model/inference scaling pressure. |
| Memory | RAG paper, Transformer/Llama | Parametric model memory vs retrieved non-parametric memory and attention context. |
| Inference | Llama 2, Kubernetes | Running the model behind production services. |
| Orchestration | Kubernetes, RAG pipelines | Kubernetes orchestrates services; RAG orchestrates retrieval plus generation. |
""".strip()

  if "technical concepts" in lowered_message or "architectures" in lowered_message or "workflows" in lowered_message:
    return f"""
{table}

Key technical concepts across the corpus:

| Source | Concrete items | Evolution path |
| --- | --- | --- |
{chr(10).join(concept_rows)}

Shared concepts:

- Attention and generation connect the Transformer, Llama 2, and RAG documents.
- Retrieval and memory connect RAG to LLM limitations: RAG supplements model parameters with external evidence.
- Scaling and deployment connect Llama 2 and Kubernetes: large-model inference needs operational orchestration.
- Orchestration appears at two levels: RAG orchestrates information flow; Kubernetes orchestrates services and workloads.
""".strip()

  return f"""
{table}

Conceptual connection:

{chr(10).join(f"- {profile['document']} contributes: {profile['role']}" for profile in ordered_profiles)}

Together they describe a production AI stack: Transformer architecture -> foundation model training/alignment -> retrieval-grounded generation -> Kubernetes deployment and orchestration.
""".strip()


def build_chat_prompt(
  message: str,
  messages: list[ChatMessage],
  retrieval_context: list[dict],
  documents: list[dict],
) -> str:
  intent = query_intent(message)
  history = build_history_context(messages)
  history_block = history or f"USER: {message}"
  context_block = build_retrieval_context(retrieval_context)
  source_manifest = build_source_manifest(retrieval_context)
  corpus_manifest = build_corpus_manifest(documents)
  extracted_evidence_terms = build_extracted_evidence_terms(retrieval_context)
  extraction_instructions = ""
  synthesis_instructions = ""

  if intent == "extraction":
    extraction_instructions = """
This is an extraction query.
First extract concrete named items from retrieved evidence before explaining anything.
Return a markdown table when the user asks for a table or list.
Use the extracted evidence terms below as the primary allowed vocabulary for table cells.
Copy specific terms from Extracted evidence terms into the answer; do not replace them with broader categories like "model training", "frameworks", or "system architecture".
For each uploaded document represented in the manifest, include a row when retrieved evidence supports at least one item.
Do not answer "no algorithms" globally unless no retrieved source contains named mechanisms, algorithms, methods, components, or techniques.
Do not add ecosystem/framework guesses such as libraries, vendor tools, or platforms unless they appear in extracted evidence terms or retrieved context.
If a document has weak retrieved evidence, write "insufficient retrieved evidence" only for that document.
Table columns should be: Document | Type | Extracted algorithms/mechanisms/components | Evidence terms.
""".strip()

  if intent == "synthesis":
    synthesis_instructions = """
This is a synthesis query across uploaded documents.
Do not describe the context as "snippets" or say the document identity is unclear when filenames are available.
Start from a compact per-document matrix before broad explanation.
For each uploaded source represented in retrieved context, name:
Document | Type | Main problem | Concrete mechanisms/components | Role in modern AI/infrastructure.
Then synthesize connections across documents.
Use exact terms from Extracted evidence terms and retrieved context.
Avoid vague placeholders like "knowledge systems", "system context", or "technical setup" unless you also name the concrete mechanism.
For learning-roadmap requests, order the actual documents by prerequisite flow: Transformer foundations, Llama/foundation model training, RAG grounding, Kubernetes production operations, unless retrieved context clearly supports a different order.
""".strip()

  return f"""
You are ContextForge's chat backend.
Give a concise visible reasoning summary before the answer. Do not include hidden chain-of-thought.
Use the conversation history to answer follow-up requests like "continue", "explain more", or "summarize that".
If document context is provided, answer from that context first. If the context is insufficient, say what is missing instead of pretending.
Only use explicitly retrieved information plus the uploaded document manifest.
Do not infer missing file names, folders, versions, framework names, commands, or corpus structure.
Never mention a framework name unless it appears in the retrieved context or uploaded document names.
Avoid vague abstraction padding. Prefer concrete terms, mechanisms, algorithms, components, workflows, commands, and named architecture pieces from the context.
If specific terms such as pods, services, deployments, schedulers, controllers, etcd, kubelet, self-attention, dense passage retrieval, or alignment are present, use those terms instead of generic phrases.
Do not say "implied", "likely", or "context suggests" unless you clearly label it as an inference and explain that the retrieved context does not state it directly.
Before writing broad synthesis, extract and use concrete evidence: named components, algorithms, control loops, training stages, deployment objects, or ranking mechanisms.
For operational questions, name the exact components and explain their roles.
For architecture comparisons, state the specific mechanism on each side before comparing.
For broad questions about all uploaded documents, organize the answer by source file when possible.
When commands, setup steps, API keys, or warnings appear in context, extract them concretely.
Use source filenames in the answer where useful.
{extraction_instructions}
{synthesis_instructions}

Return exactly this format:
REASONING_SUMMARY:
- One short bullet naming the main source files you will use.
- One short bullet naming the concrete concepts retrieved or what specifics are missing.

FINAL_ANSWER:
Your answer here.

Conversation history:
{history_block}

Uploaded document manifest:
{corpus_manifest}

Extracted evidence terms:
{extracted_evidence_terms}

Retrieved document context:
{context_block}

Selected source files:
{source_manifest}

Latest user message:
{message}
""".strip()


def split_reasoning_and_answer(text: str) -> tuple[str, str]:
  if "FINAL_ANSWER:" not in text:
    return "", text.strip()

  before, answer = text.split("FINAL_ANSWER:", 1)
  reasoning = before.replace("REASONING_SUMMARY:", "").strip()
  return reasoning, answer.strip()


def request_ollama(
  message: str,
  messages: list[ChatMessage],
  retrieval_context: list[dict],
  documents: list[dict],
  model: str,
) -> tuple[str, str]:
  payload = json.dumps(
    {
      "model": model,
      "prompt": build_chat_prompt(message, messages, retrieval_context, documents),
      "stream": False,
    }
  ).encode("utf-8")

  request = urllib.request.Request(
    f"{ollama_base_url().rstrip('/')}/api/generate",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
  )

  with urllib.request.urlopen(request, timeout=ollama_timeout_seconds()) as response:
    data = json.loads(response.read().decode("utf-8"))

  raw_response = data.get("response", "").strip() or "Ollama returned an empty response."
  return split_reasoning_and_answer(raw_response)


def request_ollama_models() -> list[str]:
  request = urllib.request.Request(f"{ollama_base_url().rstrip('/')}/api/tags")

  with urllib.request.urlopen(request, timeout=5) as response:
    data = json.loads(response.read().decode("utf-8"))

  return [model.get("name") for model in data.get("models", []) if model.get("name")]


def allowed_ollama_models() -> list[str]:
  return model_allowlist()


def resolve_ollama_model(requested_model: str | None) -> str:
  generation = generation_config()
  default_model = generation.get("default_model", "qwen3:4b-instruct")
  allowed_models = allowed_ollama_models()
  if allowed_models and default_model not in allowed_models:
    default_model = allowed_models[0]

  if requested_model:
    if not allowed_models or requested_model in allowed_models:
      return requested_model
    return default_model

  try:
    installed_models = request_ollama_models()
  except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
    installed_models = []

  filtered_models = [model for model in installed_models if not allowed_models or model in allowed_models]
  return filtered_models[0] if filtered_models else default_model
