# ContextForge V2 Baseline

Saved: 2026-05-11

## What V2 Represents

V2 is the first stable benchmarkable RAG milestone after V1.

It adds:

- Query intent routing: `general`, `synthesis`, and `extraction`.
- Deterministic synthesis for broad multi-document prompts.
- Deterministic extraction for algorithm/mechanism/component tables.
- Document-balanced synthesis retrieval for all-doc comparison and roadmap queries.
- Concrete mechanism ranking over umbrella terms.
- Kubernetes operational mechanism mapping.
- Reusable benchmark script for avoiding manual UI copy/paste.

## Snapshot Files

- `config.v2.json`
- `backend/pipeline/retrieval_v2.py`
- `backend/pipeline/generation_v2.py`
- `backend/pipeline/ingestion_v2.py`
- `backend/benchmarks/smoke_queries_v2.py`

## Benchmark Corpus

The benchmark corpus used for V2 validation:

- `00_kubernetes.pdf`
- `01_retrieval-augmented_generation_for_knowledge-intensive_nlp_tasks.pdf`
- `02_llama_2_openfoundation_and_fine-tuned_chat_models.pdf`
- `03_attention_is_all_you_need.pdf`

Observed corpus size:

- Documents: 4
- Chunks: 9706

## Benchmark Query Status

| Query Type | Expected Mode | V2 Status |
| --- | --- | --- |
| High-level comparison across all uploaded documents | `synthesis` | Good |
| Technical concepts, architectures, workflows | `synthesis` | Good |
| Practical learning roadmap | `synthesis` | Good |
| Implementation and operational comparison | `synthesis` | Good |
| Table of all algorithms | `extraction` | Good |

## Quality Notes

Strengths:

- Broad all-document prompts now produce document-level matrices instead of generic summaries.
- Algorithm extraction no longer drops Kubernetes.
- Kubernetes component evidence is mapped to operational mechanisms such as control-plane orchestration, cluster state storage, API-driven orchestration, and node reconciliation.
- Transformer/RAG/Llama mechanisms are extracted more concretely.

Performance / stability:

- V2 is the first repeatable benchmark milestone.
- Accuracy improved over V1 through synthesis/extraction routing, document-balanced retrieval, and concrete-mechanism ranking.
- Stability improved because the same benchmark query set could be run from a script instead of manual UI copy/paste.
- Latency remained high: roughly 6-8 seconds per benchmark query on the 9706-chunk corpus.

Known limitations:

- Retrieval latency is still high, roughly 6-8 seconds per benchmark query on the 9706-chunk corpus.
- The retrieval engine still recomputes BM25-style statistics per query.
- Open-ended single-question QA still depends on the general retrieval path and is less validated than the benchmark prompts.

## How To Reproduce

Run full answer benchmark checks:

```powershell
python backend\benchmarks\smoke_queries.py
```

Run retrieval-only diagnostics:

```powershell
python backend\benchmarks\smoke_queries.py --mode retrieve
```

Expected signs of V2 behavior:

- Broad benchmark prompts show `intent=synthesis`.
- Broad benchmark sources show `bm25_hierarchical_synthesis`.
- Algorithm-table prompt shows `intent=extraction`.
- Kubernetes algorithm row should not say `not found in retrieved context`.

## Next Recommended Work

1. Add a cached BM25/index layer to reduce retrieval latency.
2. Add markdown benchmark reports under `backend/reports/`.
3. Add quality gates for required document coverage and banned vague phrases.
4. Improve open-ended QA after the benchmark paths remain stable.
