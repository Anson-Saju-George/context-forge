# ContextForge V3 Baseline

Saved: 2026-05-11

## What V3 Represents

V3 is the final benchmark-focused production RAG baseline for the current project stage.

It builds on V2 with:

- Cached BM25 corpus statistics.
- Cached chunk feature extraction for technical/concrete/operational term scoring.
- MMR-style context diversity for non-synthesis retrieval.
- Forced document coverage for all-doc extraction queries.
- Deterministic synthesis for broad multi-document prompts.
- Deterministic extraction for algorithm/mechanism tables.
- Benchmark quality gates.
- Markdown benchmark reports.
- Evidence-first term extraction and generic technical scoring.

## Snapshot Files

- `config.v3.json`
- `backend/pipeline/retrieval_v3.py`
- `backend/pipeline/generation_v3.py`
- `backend/pipeline/ingestion_v3.py`
- `backend/benchmarks/smoke_queries_v3.py`

## Benchmark Corpus

- `00_kubernetes.pdf`
- `01_retrieval-augmented_generation_for_knowledge-intensive_nlp_tasks.pdf`
- `02_llama_2_openfoundation_and_fine-tuned_chat_models.pdf`
- `03_attention_is_all_you_need.pdf`

Observed corpus size:

- Documents: 4
- Chunks: 9706

## V3 Benchmark Result

Latest benchmark report:

- `backend/reports/smoke_2026-05-11_21-28-40.md`
- `backend/reports/smoke_latest.md`

Quality gates:

| Query Type | Expected Mode | Status |
| --- | --- | --- |
| High-level comparison across all uploaded documents | `synthesis` | PASS |
| Technical concepts, architectures, workflows | `synthesis` | PASS |
| Practical learning roadmap | `synthesis` | PASS |
| Implementation and operational comparison | `synthesis` | PASS |
| Table of all algorithms | `extraction` | PASS |

## Performance Notes

Cold first query still pays index/cache setup cost.

Observed benchmark behavior:

- First synthesis query: about 10.5s on the 9706-chunk corpus.
- Subsequent synthesis queries: about 160-170ms.
- Algorithm extraction after cache warmup: about 540ms.

This is a major improvement over repeated 6-8s retrieval per query in V2.

Quality / stability gains:

- Accuracy improved through cached technical/concrete/operational feature scoring, forced document coverage, and MMR-style diversity.
- Stability improved through benchmark quality gates, required source coverage checks, banned vague phrase checks, and markdown reports.
- Latency improved after cache warmup from V2's repeated 6-8s retrieval to roughly 160-170ms for warmed synthesis queries.

## Implemented Algorithm Families

Retrieval:

- BM25 sparse retrieval.
- Metadata/document-aware routing.
- Parent-child retrieval expansion.
- Document-balanced synthesis retrieval.

Ranking:

- Deterministic specificity reranking.
- Concrete mechanism boosting.
- Operational-term boosting.
- Generic/noisy-section penalties.
- MMR-style diversity selection.

Context:

- Parent/sibling context expansion.
- Source-balanced synthesis context.
- Evidence term extraction.
- Deterministic context-to-answer templates for benchmark prompts.
- Retrieved-evidence-only term use.

Evaluation:

- Benchmark query suite.
- Provider/intent checks.
- Required source coverage checks.
- Banned vague phrase checks.
- Required term checks.
- Markdown reports.

## Known Limits

- Vector ANN search is not implemented in the current local baseline.
- Cross-encoder reranking is not implemented; the current reranker is deterministic and interpretable.
- Open-ended single-document QA still uses the general retrieval path and needs more evaluation.
- The deterministic synthesis templates are excellent for benchmark questions but less flexible than full generative synthesis.

## Recommended Next Stage After V3

If continuing beyond this baseline:

1. Add real dense embeddings and vector retrieval.
2. Add RRF fusion between BM25 and vector rankings.
3. Add optional cross-encoder reranking.
4. Add persistent disk index cache instead of in-memory-only cache.
5. Add a small golden dataset for regression testing.
