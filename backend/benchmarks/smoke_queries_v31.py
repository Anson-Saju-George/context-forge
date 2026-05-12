import argparse
import textwrap
import time
from datetime import datetime
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

EXPECTED_SOURCES = {
  "00_kubernetes.pdf",
  "01_retrieval-augmented_generation_for_knowledge-intensive_nlp_tasks.pdf",
  "02_llama_2_openfoundation_and_fine-tuned_chat_models.pdf",
  "03_attention_is_all_you_need.pdf",
}

BANNED_PHRASES = [
  "snippets appear",
  "provided text appears",
  "likely related",
  "implicit",
  "implied by",
  "not found in retrieved context",
]

REQUIRED_TERMS_BY_QUERY = {
  "high_level_comparison": ["Transformer", "Llama", "RAG", "Kubernetes"],
  "technical_extraction": ["multi-head attention", "RLHF", "RAG-token", "kube-apiserver"],
  "learning_roadmap": ["study order", "Attention", "Llama", "RAG", "Kubernetes"],
  "implementation_operational_comparison": ["deployment", "retrieval", "inference", "orchestration"],
  "algorithm_table": [
    "scaled dot-product attention",
    "self-attention",
    "positional encoding",
    "PPO",
    "grouped-query attention",
    "DPR",
    "MIPS",
    "RAG-token",
    "control-plane orchestration",
  ],
}


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


def quality_gate(name: str, answer: str, provider: str, citations: list[dict]) -> tuple[str, list[str]]:
  issues = []
  answer_lower = answer.lower()
  citation_sources = {citation.get("source", "") for citation in citations}

  if name != "algorithm_table" and provider != "synthesis":
    issues.append(f"expected synthesis provider, got {provider}")
  if name == "algorithm_table" and provider != "extractor":
    issues.append(f"expected extractor provider, got {provider}")

  missing_sources = EXPECTED_SOURCES - citation_sources
  if missing_sources:
    issues.append(f"missing source coverage: {', '.join(sorted(missing_sources))}")

  banned_hits = [phrase for phrase in BANNED_PHRASES if phrase in answer_lower]
  if banned_hits:
    issues.append(f"banned vague phrases: {', '.join(banned_hits)}")

  missing_terms = [
    term
    for term in REQUIRED_TERMS_BY_QUERY.get(name, [])
    if term.lower() not in answer_lower
  ]
  if missing_terms:
    issues.append(f"missing expected terms: {', '.join(missing_terms)}")

  if "| Document |" not in answer and name in {
    "high_level_comparison",
    "technical_extraction",
    "learning_roadmap",
    "implementation_operational_comparison",
    "algorithm_table",
  }:
    issues.append("missing document table")

  if not issues:
    return "PASS", []
  if len(issues) <= 2:
    return "WARN", issues
  return "FAIL", issues


def reports_dir() -> Path:
  path = Path(__file__).resolve().parent / "reports"
  path.mkdir(parents=True, exist_ok=True)
  return path


def write_report(chat_id: str, rows: list[dict]) -> Path:
  timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
  report_path = reports_dir() / f"smoke_{timestamp}.md"
  latest_path = reports_dir() / "smoke_latest.md"

  lines = [
    f"# ContextForge Benchmark Report",
    "",
    f"- Timestamp: {timestamp}",
    f"- Chat ID: `{chat_id}`",
    "",
    "| Query | Quality | Provider | Intent | Latency ms | Selected | Issues |",
    "| --- | --- | --- | --- | ---: | ---: | --- |",
  ]

  for row in rows:
    issues = "<br>".join(row["issues"]) if row["issues"] else ""
    lines.append(
      f"| {row['name']} | {row['quality']} | {row['provider']} | {row['intent']} | "
      f"{row['latency_ms']} | {row['selected_count']} | {issues} |"
    )

  for row in rows:
    lines.extend(
      [
        "",
        f"## {row['name']}",
        "",
        "### Stats",
        "",
        "```text",
        str(row["stats"]),
        "```",
        "",
        "### Answer Preview",
        "",
        row["answer"],
        "",
        "### Sources",
        "",
        "```text",
        row["sources"],
        "```",
      ]
    )

  content = "\n".join(lines).strip() + "\n"
  report_path.write_text(content, encoding="utf-8")
  latest_path.write_text(content, encoding="utf-8")
  return report_path


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


def run_chat(chat_id: str, model: str | None, max_answer_chars: int, max_sources: int, report: bool) -> None:
  print(f"chat_id={chat_id}")
  print(f"model={model or 'backend default'}")
  print()
  report_rows = []

  for name, query in SMOKE_QUERIES:
    request = ChatRequest(
      chat_id=chat_id,
      message=textwrap.dedent(query).strip(),
      provider="ollama",
      model=model,
      use_retrieval=True,
    )
    response = chat(request)
    citation_dicts = [item.model_dump() for item in response.citations]
    quality, issues = quality_gate(name, response.answer, response.provider, citation_dicts)
    stats = {
      "provider": response.provider,
      "model": response.model,
      "fallback_used": response.fallback_used,
      "intent": response.retrieval.get("intent"),
      "candidate_k": response.retrieval.get("candidate_k"),
      "candidate_count": response.retrieval.get("candidate_count"),
      "selected_count": response.retrieval.get("selected_count"),
      "top_k": response.retrieval.get("top_k"),
      "latency_ms": response.latency_ms,
      "quality": quality,
    }

    print("=" * 88)
    print(name)
    print("-" * 88)
    print("stats:", stats)
    if issues:
      print("quality_issues:", "; ".join(issues))
    if response.reasoning_summary:
      print("reasoning_summary:")
      print(compact(response.reasoning_summary, 500))
    print("answer_preview:")
    print(compact(response.answer, max_answer_chars))
    print("sources:")
    sources = source_summary(citation_dicts, max_sources)
    print(sources)
    print()
    report_rows.append(
      {
        "name": name,
        "quality": quality,
        "issues": issues,
        "provider": response.provider,
        "intent": response.retrieval.get("intent"),
        "latency_ms": response.latency_ms,
        "selected_count": response.retrieval.get("selected_count"),
        "stats": stats,
        "answer": compact(response.answer, max_answer_chars),
        "sources": sources,
      }
    )

  if report:
    report_path = write_report(chat_id, report_rows)
    print(f"report={report_path}")


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
  parser.add_argument("--no-report", action="store_true", help="Do not write a markdown benchmark report in chat mode.")
  args = parser.parse_args()

  if args.mode == "retrieve":
    run_retrieval_only(args.chat_id, args.max_sources)
  else:
    run_chat(args.chat_id, args.model, args.max_answer_chars, args.max_sources, not args.no_report)


if __name__ == "__main__":
  main()
