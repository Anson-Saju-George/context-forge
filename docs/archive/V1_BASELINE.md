# ContextForge v1 Baseline

Saved before experimental retrieval changes.

## Snapshot files

- `config.v1.json`
- `backend/pipeline/retrieval_v1.py`
- `backend/pipeline/generation_v1.py`
- `backend/pipeline/ingestion_v1.py`

## Behavior captured

- React + FastAPI workbench
- Local Ollama chat
- PDF/DOCX/Markdown/TXT ingestion
- Section-aware chunking
- BM25 hierarchical retrieval
- Dynamic top-k
- Query intent routing
- Extraction mode
- Deterministic specificity reranking
- Backend-side evidence term extraction
- Deterministic extraction-mode table answers
- Backend `.env` config selector via `CONFIG_FILE`
- Source citations and retrieval telemetry

## Performance / Quality Notes

- Accuracy: V1 established the first usable retrieval foundation with BM25, section-aware chunking, citations, and deterministic extraction.
- Stability: Better than V0 because retrieval was no longer a single similarity pass, but benchmark gates were not yet formalized.
- Latency: No frozen benchmark latency report was captured for V1.
- Main limitation: broad cross-document synthesis and algorithm extraction were still less reliable than later versions.

## Restore notes

To restore the v1 retrieval behavior, copy the relevant `_v1.py` file back over the active file.
