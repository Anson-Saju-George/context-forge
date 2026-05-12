# ContextForge V3.1 Baseline

## What V3.1 Represents

V3.1 is the final extraction-recall baseline for the current research cycle.

The baseline emphasizes:

- evidence-first extraction
- document-balanced retrieval
- generic technical scoring and filtering
- strict benchmark quality gates
- final answers built from retrieved chunks, extracted terms, rerank metadata, and uploaded document names

## Main Changes From V3

- Added document-balanced extraction selection.
- Increased all-document extraction context from 12 to up to 16 chunks when needed.
- Preserved rerank evidence terms during extraction aggregation.
- Prioritized concrete mechanisms over umbrella concepts in algorithm extraction.

## Benchmark Result

Latest passing run:

```text
backend/reports/smoke_2026-05-12_09-50-48.md
```

All five benchmark queries passed:

- high-level comparison
- technical extraction
- learning roadmap
- implementation/operational comparison
- algorithm table

Strict algorithm-table gate passed with:

- scaled dot-product attention
- self-attention
- positional encoding
- grouped-query attention
- RLHF
- PPO
- DPR
- MIPS
- RAG-token
- control-plane orchestration

## Performance / Quality Notes

Latest passing run on the 9706-chunk benchmark corpus:

| Query | Quality | Latency |
| --- | --- | ---: |
| High-level comparison | PASS | 10141ms |
| Technical extraction | PASS | 164ms |
| Learning roadmap | PASS | 164ms |
| Implementation/operational comparison | PASS | 194ms |
| Algorithm table | PASS | 579ms |

Compared with V3:

- Accuracy improved for extraction-heavy prompts through document-balanced extraction selection and concrete mechanism prioritization.
- Stability improved through stricter algorithm-table gates and preserved rerank evidence terms.
- Latency stayed in the same warmed-query range as V3: sub-200ms for warmed synthesis queries and sub-second for algorithm extraction.
- The first query still pays cache setup cost.

## Saved Files

- `config.v3.1.json`
- `backend/pipeline/retrieval_v31.py`
- `backend/pipeline/generation_v31.py`
- `backend/pipeline/ingestion_v31.py`
- `backend/benchmarks/smoke_queries_v31.py`
