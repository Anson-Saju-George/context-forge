import math
import re


def tokenize(text: str) -> list[str]:
  return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def term_counts(tokens: list[str]) -> dict[str, int]:
  counts = {}
  for token in tokens:
    counts[token] = counts.get(token, 0) + 1
  return counts


def cosine_similarity(left: dict[str, int], right: dict[str, int]) -> float:
  if not left or not right:
    return 0.0

  overlap = set(left) & set(right)
  dot = sum(left[token] * right[token] for token in overlap)
  left_norm = math.sqrt(sum(value * value for value in left.values()))
  right_norm = math.sqrt(sum(value * value for value in right.values()))
  if not left_norm or not right_norm:
    return 0.0
  return dot / (left_norm * right_norm)


def retrieve_context(query: str, chunks: list[dict], requested_top_k: int | None = None) -> tuple[list[dict], dict]:
  top_k = requested_top_k or 6
  query_counts = term_counts(tokenize(query))
  scored = []

  for chunk in chunks:
    text = f"{chunk.get('section', '')}\n{chunk.get('text', '')}"
    score = cosine_similarity(query_counts, term_counts(tokenize(text)))
    if score <= 0:
      continue

    scored.append(
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
        "rerank_score": round(score, 4),
        "rerank_reasons": ["toy_similarity_baseline", "cosine_token_overlap"],
      }
    )

  scored.sort(key=lambda item: item["score"], reverse=True)
  selected = scored[:top_k]
  return selected, {
    "mode": "v0_token_similarity",
    "intent": "general",
    "candidate_k": len(chunks),
    "candidate_count": len(scored),
    "reranked_count": len(scored),
    "selected_count": len(selected),
    "top_k": top_k,
    "total_chunks": len(chunks),
  }

