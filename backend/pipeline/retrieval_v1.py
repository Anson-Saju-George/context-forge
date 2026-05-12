import math
import re
from typing import Literal

try:
  from .config import settings
except ImportError:
  from config import settings


TECHNICAL_TERMS = {
  "api",
  "api server",
  "attention",
  "autoregressive",
  "controller",
  "controller manager",
  "crd",
  "deployment",
  "dense passage retrieval",
  "dpr",
  "embedding",
  "encoder",
  "decoder",
  "etcd",
  "fine-tuning",
  "generation",
  "ingress",
  "inference",
  "kube-apiserver",
  "kube-controller-manager",
  "kube-scheduler",
  "kubelet",
  "llama",
  "multi-head attention",
  "node",
  "pod",
  "pods",
  "policy",
  "pretraining",
  "rag",
  "retriever",
  "rlhf",
  "scheduler",
  "self-attention",
  "service",
  "services",
  "taint",
  "toleration",
  "token",
  "transformer",
  "value",
  "query",
  "key",
  "algorithm",
  "algorithms",
  "autoscaling",
  "backpropagation",
  "beam search",
  "classifier",
  "control loop",
  "load balancing",
  "mechanism",
  "method",
  "methods",
  "optimizer",
  "ppo",
  "reconciliation",
  "rejection sampling",
  "sampling",
  "scaled dot-product attention",
  "technique",
  "top-k",
}

GENERIC_TERMS = {
  "advanced",
  "application",
  "applications",
  "architecture",
  "context",
  "framework",
  "important",
  "infrastructure",
  "management",
  "modern",
  "overview",
  "process",
  "robust",
  "solution",
  "system",
  "systems",
  "technology",
  "workflow",
}

EXTRACTION_MARKERS = [
  "all algorithms",
  "all components",
  "all mechanisms",
  "all methods",
  "all techniques",
  "architectures",
  "commands",
  "components",
  "extract",
  "list",
  "make a table",
  "mechanisms",
  "methods",
  "operators",
  "table",
  "techniques",
]

SECTION_BOOST_TERMS = {
  "algorithm",
  "architecture",
  "attention",
  "autoscaling",
  "component",
  "control plane",
  "deployment",
  "evaluation",
  "experiment",
  "implementation",
  "inference",
  "method",
  "model",
  "orchestration",
  "pretraining",
  "retrieval",
  "scheduler",
  "scheduling",
  "training",
}

SECTION_PENALTY_TERMS = {
  "abstract",
  "acknowledgement",
  "acknowledgements",
  "conclusion",
  "contents",
  "copyright",
  "foreword",
  "glossary",
  "introduction",
  "overview",
  "preface",
  "references",
  "related work",
  "summary",
}


def tokenize(text: str) -> list[str]:
  return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def query_intent(query: str) -> Literal["extraction", "general"]:
  lowered_query = query.lower()
  if any(marker in lowered_query for marker in EXTRACTION_MARKERS):
    return "extraction"
  return "general"


def bm25_retrieve(query: str, chunks: list[dict], top_k: int) -> list[dict]:
  query_terms = tokenize(query)
  if not query_terms or not chunks:
    return []

  tokenized_chunks = [tokenize(chunk.get("text", "")) for chunk in chunks]
  doc_lengths = [len(tokens) for tokens in tokenized_chunks]
  average_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0
  document_frequencies = {}

  for tokens in tokenized_chunks:
    for term in set(tokens):
      document_frequencies[term] = document_frequencies.get(term, 0) + 1

  scored_results = []
  total_docs = len(chunks)
  k1 = 1.5
  b = 0.75

  for chunk, tokens, doc_length in zip(chunks, tokenized_chunks, doc_lengths, strict=False):
    term_counts = {}
    for token in tokens:
      term_counts[token] = term_counts.get(token, 0) + 1

    score = 0.0
    for term in query_terms:
      term_frequency = term_counts.get(term, 0)
      if not term_frequency:
        continue

      doc_frequency = document_frequencies.get(term, 0)
      idf = math.log(1 + (total_docs - doc_frequency + 0.5) / (doc_frequency + 0.5))
      denominator = term_frequency + k1 * (
        1 - b + b * (doc_length / average_doc_length if average_doc_length else 0)
      )
      score += idf * ((term_frequency * (k1 + 1)) / denominator)

    if score > 0:
      scored_results.append(
        {
          "chunk_id": chunk.get("id", ""),
          "document_id": chunk.get("document_id", ""),
          "source": chunk.get("source", ""),
          "original_filename": chunk.get("original_filename", ""),
          "text": chunk.get("text", ""),
          "score": round(score, 4),
          "page": chunk.get("page"),
          "section": chunk.get("section", ""),
          "parent_id": chunk.get("parent_id", ""),
          "chunk_index": chunk.get("chunk_index", 0),
        }
      )

  scored_results.sort(key=lambda item: item["score"], reverse=True)
  return scored_results[:top_k]


def query_broadness_score(query: str) -> int:
  lowered_query = query.lower()
  score = 0

  broad_markers = [
    "all uploaded",
    "all documents",
    "all docs",
    "overview",
    "compare",
    "learning path",
    "cheat sheet",
    "summarize",
    "changelog",
    "evolved",
    "over time",
    "classify",
    "each file",
    "multiple documents",
  ]

  score += sum(1 for marker in broad_markers if marker in lowered_query)
  score += min(3, lowered_query.count("?"))
  score += min(3, len(re.findall(r"\n|:", query)) // 2)
  return score


def adaptive_top_k(query: str, total_chunks: int = 0, default_k: int = 6) -> int:
  max_top_k = min(settings()["config"].get("limits", {}).get("max_top_k", 10), 12)
  score = query_broadness_score(query)
  lowered_query = query.lower()
  precise_markers = [
    "how does",
    "explain how",
    "what is",
    "define",
    "scheduler",
    "kubelet",
    "etcd",
    "pod",
    "service",
    "deployment",
    "ingress",
    "attention",
    "self-attention",
    "dense passage",
    "alignment",
  ]

  requested_k = default_k + min(score * 2, 6)
  if any(marker in lowered_query for marker in precise_markers):
    requested_k = min(requested_k, 8)
  if total_chunks >= 1000 and score >= 2:
    requested_k = min(max(requested_k, 9), max_top_k)
  return max(default_k, min(requested_k, max_top_k))


def diversify_results(results: list[dict], top_k: int, broad_query: bool) -> list[dict]:
  if not broad_query or len(results) <= top_k:
    return results[:top_k]

  per_source_limit = 3
  selected = []
  selected_ids = set()
  source_counts = {}

  for result in results:
    source = result.get("source", "")
    if source in source_counts:
      continue

    selected.append(result)
    selected_ids.add(result.get("chunk_id"))
    source_counts[source] = 1

    if len(selected) >= top_k:
      return selected

  for result in results:
    chunk_id = result.get("chunk_id")
    source = result.get("source", "")

    if chunk_id in selected_ids:
      continue

    if source_counts.get(source, 0) >= per_source_limit:
      continue

    selected.append(result)
    selected_ids.add(chunk_id)
    source_counts[source] = source_counts.get(source, 0) + 1

    if len(selected) >= top_k:
      return selected

  for result in results:
    chunk_id = result.get("chunk_id")
    if chunk_id in selected_ids:
      continue

    selected.append(result)
    selected_ids.add(chunk_id)

    if len(selected) >= top_k:
      break

  return selected


def query_document_hints(query: str, chunks: list[dict]) -> set[str]:
  lowered_query = query.lower()
  hints = set()

  if query_intent(query) == "extraction" and any(
    marker in lowered_query
    for marker in [
      "all docs",
      "all documents",
      "these docs",
      "these documents",
      "uploaded docs",
      "uploaded documents",
    ]
  ):
    return {chunk.get("document_id", "") for chunk in chunks if chunk.get("document_id")}

  return hints


def boost_candidates(query: str, candidates: list[dict], document_hints: set[str]) -> list[dict]:
  query_terms = set(tokenize(query))
  boosted = []

  for candidate in candidates:
    text_terms = set(tokenize(candidate.get("text", "")[:2000]))
    section_terms = set(tokenize(candidate.get("section", "")))
    exact_overlap = len(query_terms & (text_terms | section_terms))
    score = float(candidate.get("score", 0))

    if candidate.get("document_id") in document_hints:
      score *= 1.18

    if exact_overlap:
      score *= 1 + min(exact_overlap * 0.04, 0.24)

    boosted_item = {**candidate, "score": round(score, 4)}
    boosted.append(boosted_item)

  boosted.sort(key=lambda item: item["score"], reverse=True)
  return boosted


def find_term_hits(text: str, terms: set[str]) -> list[str]:
  lowered_text = text.lower()
  hits = []

  for term in terms:
    if " " in term:
      if term in lowered_text:
        hits.append(term)
      continue

    if re.search(rf"\b{re.escape(term)}\b", lowered_text):
      hits.append(term)

  return sorted(hits)


def acronym_count(text: str) -> int:
  return len(re.findall(r"\b[A-Z][A-Z0-9-]{1,}\b", text))


def specificity_rerank(
  query: str,
  candidates: list[dict],
  document_hints: set[str],
  intent: Literal["extraction", "general"],
) -> list[dict]:
  query_terms = set(tokenize(query))
  reranked = []
  extraction_mode = intent == "extraction"

  for candidate in candidates:
    text = candidate.get("text", "")
    section = candidate.get("section", "")
    combined_text = f"{section}\n{text}"
    combined_terms = set(tokenize(combined_text))
    section_terms = set(tokenize(section))
    text_length = max(len(combined_terms), 1)
    exact_overlap = query_terms & combined_terms
    section_overlap = query_terms & section_terms
    technical_hits = find_term_hits(combined_text, TECHNICAL_TERMS)
    generic_hits = find_term_hits(combined_text, GENERIC_TERMS)
    section_boost_hits = find_term_hits(section, SECTION_BOOST_TERMS)
    section_penalty_hits = find_term_hits(section, SECTION_PENALTY_TERMS)
    acronyms = acronym_count(combined_text)
    generic_density = len(generic_hits) / text_length

    bm25_score = float(candidate.get("score", 0))
    rerank_score = bm25_score
    rerank_score += len(exact_overlap) * 2.4
    rerank_score += len(section_overlap) * 3.2
    rerank_score += min(len(technical_hits), 12) * 1.8
    rerank_score += min(len(section_boost_hits), 4) * 2.5

    if extraction_mode:
      rerank_score += min(len(technical_hits), 16) * 2.2
      rerank_score += min(acronyms, 10) * 0.8
      rerank_score += min(len(section_boost_hits), 5) * 3.0
      rerank_score -= min(len(section_penalty_hits), 3) * 4.0
    else:
      rerank_score -= min(len(section_penalty_hits), 2) * 1.5

    if candidate.get("document_id") in document_hints:
      rerank_score += 4.0

    if len(text) < 220:
      rerank_score -= 3.0

    if generic_density > 0.08:
      rerank_score -= min(generic_density * 30, 5.0)

    reasons = []
    if exact_overlap:
      reasons.append(f"query_terms={len(exact_overlap)}")
    if section_overlap:
      reasons.append(f"section_terms={len(section_overlap)}")
    if technical_hits:
      reasons.append(f"technical={', '.join(technical_hits[:5])}")
    if acronyms and extraction_mode:
      reasons.append(f"acronyms={acronyms}")
    if section_boost_hits:
      reasons.append(f"section_boost={', '.join(section_boost_hits[:3])}")
    if section_penalty_hits:
      reasons.append(f"section_penalty={', '.join(section_penalty_hits[:3])}")
    if candidate.get("document_id") in document_hints:
      reasons.append("document_hint")
    if extraction_mode:
      reasons.append("extraction_mode")
    if generic_density > 0.08:
      reasons.append("generic_penalty")

    reranked.append(
      {
        **candidate,
        "rerank_score": round(rerank_score, 4),
        "rerank_reasons": reasons,
      }
    )

  reranked.sort(key=lambda item: item.get("rerank_score", item.get("score", 0)), reverse=True)
  return reranked


def merge_candidates(*candidate_groups: list[dict]) -> list[dict]:
  merged = {}

  for group in candidate_groups:
    for candidate in group:
      chunk_id = candidate.get("chunk_id")
      if not chunk_id:
        continue

      existing = merged.get(chunk_id)
      if not existing or float(candidate.get("score", 0)) > float(existing.get("score", 0)):
        merged[chunk_id] = candidate

  candidates = list(merged.values())
  candidates.sort(key=lambda item: item.get("score", 0), reverse=True)
  return candidates


def select_by_score_shape(candidates: list[dict], target_k: int) -> list[dict]:
  if not candidates:
    return []

  selected = []
  best_score = max(float(candidates[0].get("rerank_score", candidates[0].get("score", 0))), 0.0001)
  previous_score = best_score

  for candidate in candidates:
    score = float(candidate.get("rerank_score", candidate.get("score", 0)))
    selected_count = len(selected)
    score_ratio = score / best_score
    sharp_drop = selected_count >= 4 and previous_score and score / previous_score < 0.62
    too_weak = selected_count >= 5 and score_ratio < 0.38

    if selected_count >= target_k or sharp_drop or too_weak:
      break

    selected.append(candidate)
    previous_score = score

  return selected or candidates[: min(target_k, len(candidates))]


def expand_parent_context(selected: list[dict], chunks: list[dict], max_chars: int = 1600) -> list[dict]:
  chunks_by_id = {chunk.get("id"): chunk for chunk in chunks}
  chunks_by_parent = {}

  for chunk in chunks:
    parent_id = chunk.get("parent_id")
    if parent_id:
      chunks_by_parent.setdefault(parent_id, []).append(chunk)

  expanded = []
  for result in selected:
    chunk_id = result.get("chunk_id")
    source_chunk = chunks_by_id.get(chunk_id)
    if not source_chunk:
      expanded.append(result)
      continue

    parent_id = source_chunk.get("parent_id")
    sibling_chunks = sorted(
      chunks_by_parent.get(parent_id, [source_chunk]),
      key=lambda item: item.get("chunk_index", 0),
    )
    source_index = source_chunk.get("chunk_index", 0)
    nearby = [
      chunk
      for chunk in sibling_chunks
      if abs(chunk.get("chunk_index", 0) - source_index) <= 1
    ]

    context = "\n\n".join(chunk.get("text", "") for chunk in nearby).strip()
    if len(context) > max_chars:
      context = context[:max_chars].rsplit(" ", 1)[0].strip()

    expanded.append(
      {
        **result,
        "text": context or result.get("text", ""),
        "page": source_chunk.get("page"),
        "section": source_chunk.get("section", ""),
        "parent_id": source_chunk.get("parent_id", ""),
      }
    )

  return expanded


def retrieve_context(query: str, chunks: list[dict], requested_top_k: int | None = None) -> tuple[list[dict], dict]:
  intent = query_intent(query)
  target_k = requested_top_k or adaptive_top_k(query, len(chunks))
  if intent == "extraction":
    target_k = max(target_k, min(12, settings()["config"].get("limits", {}).get("max_top_k", 12)))
  candidate_k = min(len(chunks), max(40, target_k * 6))
  if intent == "extraction":
    candidate_k = min(len(chunks), max(120, target_k * 10))
  raw_candidates = bm25_retrieve(query, chunks, candidate_k)
  document_hints = query_document_hints(query, chunks)
  broad_query = query_broadness_score(query) >= 2 or len(document_hints) > 1
  routed_candidates = []

  for document_id in document_hints:
    document_chunks = [chunk for chunk in chunks if chunk.get("document_id") == document_id]
    routed_candidates.extend(bm25_retrieve(query, document_chunks, min(16, len(document_chunks))))

  merged_candidates = merge_candidates(raw_candidates, routed_candidates)
  boosted_candidates = boost_candidates(query, merged_candidates, document_hints)
  if document_hints:
    hinted_candidates = [
      candidate for candidate in boosted_candidates if candidate.get("document_id") in document_hints
    ]
    other_candidates = [
      candidate for candidate in boosted_candidates if candidate.get("document_id") not in document_hints
    ]
    boosted_candidates = hinted_candidates if len(hinted_candidates) >= target_k else hinted_candidates + other_candidates
  reranked_candidates = specificity_rerank(query, boosted_candidates, document_hints, intent)
  diverse_candidates = diversify_results(reranked_candidates, max(target_k * 2, target_k), broad_query)
  selected = select_by_score_shape(diverse_candidates, target_k)
  expanded = expand_parent_context(
    selected,
    chunks,
    max_chars=900 if intent == "extraction" else 1600,
  )

  stats = {
    "mode": "bm25_hierarchical",
    "intent": intent,
    "candidate_k": candidate_k,
    "candidate_count": len(merged_candidates),
    "routed_documents": len(document_hints),
    "reranked_count": len(reranked_candidates),
    "selected_count": len(expanded),
    "top_k": target_k,
    "total_chunks": len(chunks),
  }
  return expanded, stats
