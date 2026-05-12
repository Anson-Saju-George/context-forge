import argparse
import textwrap
import time
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
  sys.path.insert(0, str(BACKEND_DIR))

from main import chat
from models import ChatRequest
from pipeline.retrieval import retrieve_context
from storage import chunks_path, load_json


SMOKE_QUERIES = [
  (
    "high_level_comparison",
    """
Give me a complete high-level comparison of all uploaded documents.

Explain:
- what each document is about
- whether it is research-focused, implementation-focused, or operational
- the main problems each document tries to solve
- the core concepts introduced in each document
- how the documents relate to modern AI systems and infrastructure

Compare the papers conceptually and explain how they connect together.
""",
  ),
  (
    "technical_extraction",
    """
Extract the most important technical concepts, architectures, algorithms, and workflows from all uploaded documents.

Include:
- transformer architecture
- retrieval-augmented generation pipelines
- Kubernetes orchestration concepts
- Llama 2 training/alignment ideas
- scaling, inference, deployment, or distributed system concepts

Explain which concepts appear across multiple documents and how they evolved.
""",
  ),
  (
    "learning_roadmap",
    """
Create a practical learning roadmap using all uploaded documents.

Explain:
- what order I should study the documents in
- what beginner, intermediate, and advanced concepts appear
- what prerequisites I need before reading each document
- which documents are theoretical vs implementation-heavy
- what projects or systems I should build after each stage

Design the roadmap for someone who wants to build production-grade AI systems.
""",
  ),
  (
    "implementation_operational_comparison",
    """
Compare the implementation and operational ideas across all uploaded documents.

Explain:
- how Kubernetes infrastructure relates to modern AI systems
- how RAG systems interact with transformer-based models
- how Llama 2 relates to the original transformer architecture
- where deployment, retrieval, scaling, memory, inference, and orchestration appear across the documents

Identify overlapping concepts, complementary ideas, and important differences.
""",
  ),
  (
    "algorithm_table",
    "make a table of all algorithms mention in these docs",
  ),
]


def compact(text: str, max_chars: int) -> str:
  cleaned = "\n".join(line.rstrip() for line in text.strip().splitlines())
  if len(cleaned) <= max_chars:
    return cleaned
  return cleaned[:max_chars].rstrip() + "\n..."


def source_summary(results: list[dict], limit: int) -> str:
  rows = []
  for index, result in enumerate(results[:limit], start=1):
    score = result.get("rerank_score", result.get("score", 0))
    section = result.get("section", "")
    source = result.get("source", "")
    reasons = ", ".join(result.get("rerank_reasons", [])[:3])
    rows.append(f"{index}. {source} | score={score} | section={section} | {reasons}")
  return "\n".join(rows) if rows else "No sources selected."


def run_retrieval_only(chat_id: str, max_sources: int) -> None:
  chunks = load_json(chunks_path(chat_id), [])
  print(f"chat_id={chat_id}")
  print(f"chunks={len(chunks)}")
  print()

  for name, query in SMOKE_QUERIES:
    start = time.perf_counter()
    results, stats = retrieve_context(textwrap.dedent(query).strip(), chunks)
    latency_ms = int((time.perf_counter() - start) * 1000)

    print("=" * 88)
    print(name)
    print("-" * 88)
    print(
      "stats:",
      {
        "intent": stats.get("intent"),
        "candidate_k": stats.get("candidate_k"),
        "candidate_count": stats.get("candidate_count"),
        "reranked_count": stats.get("reranked_count"),
        "selected_count": stats.get("selected_count"),
        "top_k": stats.get("top_k"),
        "latency_ms": latency_ms,
      },
    )
    print(source_summary(results, max_sources))
    print()


def run_chat(chat_id: str, model: str | None, max_answer_chars: int, max_sources: int) -> None:
  print(f"chat_id={chat_id}")
  print(f"model={model or 'backend default'}")
  print()

  for name, query in SMOKE_QUERIES:
    request = ChatRequest(
      chat_id=chat_id,
      message=textwrap.dedent(query).strip(),
      provider="ollama",
      model=model,
      use_retrieval=True,
    )
    response = chat(request)

    print("=" * 88)
    print(name)
    print("-" * 88)
    print(
      "stats:",
      {
        "provider": response.provider,
        "model": response.model,
        "fallback_used": response.fallback_used,
        "intent": response.retrieval.get("intent"),
        "candidate_k": response.retrieval.get("candidate_k"),
        "candidate_count": response.retrieval.get("candidate_count"),
        "selected_count": response.retrieval.get("selected_count"),
        "top_k": response.retrieval.get("top_k"),
        "latency_ms": response.latency_ms,
      },
    )
    if response.reasoning_summary:
      print("reasoning_summary:")
      print(compact(response.reasoning_summary, 500))
    print("answer_preview:")
    print(compact(response.answer, max_answer_chars))
    print("sources:")
    print(source_summary([item.model_dump() for item in response.citations], max_sources))
    print()


def main() -> None:
  parser = argparse.ArgumentParser(description="Run ContextForge benchmark queries against the current corpus.")
  parser.add_argument("--chat-id", default="default", help="Chat/corpus id to test.")
  parser.add_argument(
    "--mode",
    choices=["retrieve", "chat"],
    default="chat",
    help="Use chat for full answer generation, or retrieve for fast evidence checks.",
  )
  parser.add_argument("--model", default=None, help="Ollama model name for chat mode.")
  parser.add_argument("--max-answer-chars", type=int, default=2600)
  parser.add_argument("--max-sources", type=int, default=5)
  args = parser.parse_args()

  if args.mode == "retrieve":
    run_retrieval_only(args.chat_id, args.max_sources)
  else:
    run_chat(args.chat_id, args.model, args.max_answer_chars, args.max_sources)


if __name__ == "__main__":
  main()
