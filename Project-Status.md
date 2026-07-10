# Project Status - ContextForge

**Last audited:** 2026-07-10  
**Audited against commit:** `e199843`

## 1. What this project actually is

ContextForge is a React/Vite + FastAPI local RAG workbench for uploading `.md`, `.mdx`, `.txt`, `.pdf`, and `.docx` files, comparing versioned retrieval implementations (`v0`, `v1`, `v2`, `v3`, `v3.1`), and generating cited answers through deterministic extraction/synthesis paths or Ollama. This is grounded in the frontend package/scripts (`package.json:6`, `package.json:12`), backend routes (`backend/main.py:177` through `backend/main.py:482`), upload suffix allowlist (`backend/pipeline/ingestion.py:8`), RAG version registry (`backend/main.py:49`), and generation path selection (`backend/main.py:523`, `backend/main.py:531`, `backend/main.py:544`).

## 2. Current implementation state

| Area | Verified state | Source |
| --- | --- | --- |
| Frontend runtime | React 19 + Vite 8 app with `dev`, `build`, `lint`, and `preview` scripts. | `package.json:6`, `package.json:12`, `package.json:19` |
| Frontend base path | Vite builds with `base: '/context-forge/'`. | `vite.config.js:6` |
| Frontend API client | Reads `routing` from `config.json`; defaults to `http://localhost:8000` in dev and `/context-forge/api` prefix. | `src/lib/api.js:1`, `src/lib/api.js:4`, `src/lib/api.js:5` |
| Backend runtime | FastAPI app in `backend/main.py`; direct script mode binds `127.0.0.1:8000`. | `backend/main.py:129`, `backend/main.py:588` |
| Backend mount/base path | API prefix comes from config/env and is `/context-forge/api` in `config.json`. Docs path is `/context-forge/api/docs`. | `backend/config.py:118`, `config.json:16`, `config.json:17` |
| Docker/compose | No `Dockerfile` or `docker-compose*.yml` exists in the audited tree. | `Test-Path Dockerfile` / `Test-Path docker-compose.yml` returned `False` |
| Inference backend | Ollama is configured by default with `qwen3:4b-instruct` and `http://localhost:11434`; deterministic extraction/synthesis paths can bypass Ollama for extraction/synthesis intents when provider is `auto`. | `config.json:72`, `config.json:73`, `backend/main.py:523`, `backend/main.py:531`, `backend/main.py:544` |
| Model allowlist | `OLLAMA_MODEL_ALLOWLIST` is read from env; if empty, no explicit allowlist is returned. | `backend/config.py:152`, `backend/pipeline/generation.py:953` |
| Storage: uploads/chunks | Documents and chunks are JSON/file based under configured storage (`data/chats`), not SQLite. | `config.json:42`, `backend/storage.py:12`, `backend/storage.py:25`, `backend/storage.py:29`, `backend/main.py:447`, `backend/main.py:448` |
| Storage: user/usage DB | SQLite file is `data/contextforge.db`; it stores `users` and `usage_events`. | `backend/db.py:8`, `backend/db.py:25`, `backend/db.py:43` |
| Auth mode | If auth is disabled, backend returns a local development user. Auth is enabled only when `backend/secrets.env` exists and `GOOGLE_CLIENT_ID` is set. | `backend/auth.py:29`, `backend/auth.py:108`, `backend/config.py:168` |
| Google login | Implemented as `POST /auth/google` with a Google credential payload, not `/auth/google/start` and callback routes. | `backend/main.py:249`, `backend/models.py:52`, `src/lib/api.js:116` |
| Sessions/JWT | Custom HMAC-signed session token, not `python-jose`. Local dev auto-generates a JWT/session secret if missing. | `backend/auth.py:45`, `backend/auth.py:53`, `backend/config.py:105` |
| Payment | Razorpay order and payment verification endpoints exist. There is no webhook endpoint in code. | `backend/main.py:286`, `backend/main.py:332` |
| Access/entitlement | First login can grant one free entitlement window; payment extends entitlement by `AUTH_SESSION_SECONDS` (default 3600). This is time-window access, not implemented as "2 free chats / paid max 5 chats." | `backend/db.py:83`, `backend/db.py:91`, `backend/db.py:125`, `backend/config.py:128` |
| Upload limits | `MAX_UPLOAD_FILES` env controls max upload/workspace files; default is 5. | `backend/config.py:139`, `backend/main.py:400` |
| File naming | Uploaded files are stored as `NN_sanitized_name.ext`. | `backend/main.py:422`, `backend/pipeline/ingestion.py:11` |
| Retrieval | Active default is `v3.1`; active retrieval code is BM25/hierarchical with deterministic reranking/diversity. There is no Qdrant/vector embedding implementation in active code. | `backend/main.py:49`, `backend/main.py:77`, `backend/pipeline/retrieval.py:167`, `backend/pipeline/retrieval.py:731` |

## 3. Endpoints / API

The API prefix is configurable; with current `config.json`, the prefix is `/context-forge/api` (`config.json:16`, `backend/main.py:143`).

| Method | Route with current prefix | Purpose | Source |
| --- | --- | --- | --- |
| GET | `/context-forge/api/health` | Health and environment. | `backend/main.py:177` |
| GET | `/context-forge/api/config` | Active config and runtime secret status flags. | `backend/main.py:186` |
| GET | `/context-forge/api/capabilities` | Resolved capabilities. | `backend/main.py:198` |
| GET | `/context-forge/api/models` | Ollama/default model metadata. | `backend/main.py:203` |
| GET | `/context-forge/api/rag-versions` | Version catalog for `v0` through `v3.1`. | `backend/main.py:234` |
| POST | `/context-forge/api/auth/google` | Google credential login. | `backend/main.py:249` |
| GET | `/context-forge/api/auth/me` | Current authenticated user. | `backend/main.py:263` |
| GET | `/context-forge/api/usage/me` | Usage counters and entitlement data. | `backend/main.py:268` |
| POST | `/context-forge/api/payment/order` | Create Razorpay order. | `backend/main.py:286` |
| POST | `/context-forge/api/payment/verify` | Verify Razorpay payment signature and extend entitlement. | `backend/main.py:332` |
| GET | `/context-forge/api/documents` | List documents/chunks for a chat. | `backend/main.py:360` |
| POST | `/context-forge/api/documents/clear` | Clear a chat's stored documents. | `backend/main.py:374` |
| POST | `/context-forge/api/ingest` | Upload and chunk files. | `backend/main.py:389` |
| POST | `/context-forge/api/retrieve` | Retrieve context for a query. | `backend/main.py:459` |
| POST | `/context-forge/api/chat` | Retrieve and answer. | `backend/main.py:482` |

## 4. Verified metrics / benchmarks

Only metrics traceable to committed docs or generated reports are listed here. I did not re-run benchmarks during this audit.

| Metric / claim | Source | Status |
| --- | --- | --- |
| V3.1 latest passing tracked baseline cites `backend/reports/smoke_2026-05-12_09-50-48.md`. | `V3_1_BASELINE.md:24` | Historical/tracked claim; source report is generated and ignored. |
| V3.1 baseline reports five benchmark queries passed and latencies: 10141ms, 164ms, 164ms, 194ms, 579ms. | `V3_1_BASELINE.md:57` through `V3_1_BASELINE.md:61` | Historical/tracked claim; not re-run. |
| V3 baseline reports warmed synthesis queries around 160-170ms and algorithm extraction about 540ms. | `V3_BASELINE.md:64`, `V3_BASELINE.md:65`, `V3_BASELINE.md:66` | Historical/tracked claim; not re-run. |
| Qwen forced-Ollama run reported V0-V3.1 latencies from archived output. | `Output.md:88` through `Output.md:94` | Historical/tracked claim; not re-run. |
| Generated benchmark reports exist under `backend/reports/`, but that directory is gitignored. | `.gitignore:29`, inventory command output | Archived as generated historical output; not treated as active status. |

UNVERIFIED: Any benchmark number not listed above, any current production latency, any hosted deployment benchmark, and any claim that the current environment has Ollama or a specific model installed.

## 5. Configuration

### Active JSON config

| Config | Value | Source |
| --- | --- | --- |
| Deployment profile | `local_dev` | `config.json:2` |
| Frontend base path | `/context-forge` | `config.json:14`; Vite uses `/context-forge/` at `vite.config.js:6` |
| API base URL | empty string | `config.json:15` |
| API prefix | `/context-forge/api` | `config.json:16` |
| Docs path | `/context-forge/api/docs` | `config.json:17` |
| CORS origins | `http://localhost:5173`, `http://127.0.0.1:5173` | `config.json:19` |
| Max top-k configured | `20`; backend caps request top-k to at most `12`. | `config.json:32`, `backend/main.py:464` |
| Storage base dir | `data/chats` | `config.json:42` |
| Default generation provider | `ollama` | `config.json:71` |
| Default generation model | `qwen3:4b-instruct` | `config.json:72` |
| Ollama base URL | `http://localhost:11434` | `config.json:73`, `backend/pipeline/generation.py:12` |

### Environment variables

The backend manually loads `.env`, `backend/.env`, and `backend/secrets.env` (`backend/config.py:10`, `backend/config.py:11`, `backend/config.py:12`, `backend/config.py:27`). The tracked example is `backend/secrets.env.example`.

| Variable | Effect | Source |
| --- | --- | --- |
| `CONFIG_FILE` | Select active JSON config; default `config.json`. | `backend/config.py:35` |
| `FRONTEND_BASE_PATH` | Overrides config routing frontend base path. | `backend/config.py:81` |
| `API_BASE_URL` | Overrides config routing API base URL. | `backend/config.py:82` |
| `API_PREFIX` | Overrides config routing API prefix. | `backend/config.py:83` |
| `STORAGE_BASE_DIR` | Overrides storage base dir. | `backend/config.py:84` |
| `JWT_SECRET` | Session signing secret; generated only in `local_dev` if missing. | `backend/config.py:105` |
| `GOOGLE_CLIENT_ID` | Enables Google auth when `backend/secrets.env` exists. | `backend/config.py:126`, `backend/config.py:168` |
| `GOOGLE_ALLOWED_DOMAIN` | Optional hosted-domain restriction. | `backend/config.py:127`, `backend/auth.py:151` |
| `AUTH_SESSION_SECONDS` | Entitlement/session duration; default 3600. | `backend/config.py:128` |
| `ADMIN_EMAILS` or `admin` | Admin allowlist. | `backend/config.py:129` |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | Enables payment when auth is enabled. | `backend/config.py:134`, `backend/config.py:135`, `backend/auth.py:34` |
| `RAZORPAY_AMOUNT_PAISE` / `RAZORPAY_CURRENCY` | Razorpay amount/currency; defaults 2000 / INR. | `backend/config.py:137`, `backend/config.py:138` |
| `MAX_UPLOAD_FILES` | Max files in workspace/upload flow; default 5. | `backend/config.py:139` |
| `MAX_ACTIVE_CLIENTS` | Generation semaphore size; default min 1. | `backend/config.py:140`, `backend/main.py:125` |
| `VRAM_AVAILABLE_GB` / `VRAM_REQUIRED_GB` | Blocks generation if configured VRAM is insufficient. | `backend/config.py:141`, `backend/config.py:142`, `backend/main.py:145` |
| `OLLAMA_MODEL_ALLOWLIST` | Limits displayed/allowed Ollama models. | `backend/config.py:152`, `backend/pipeline/generation.py:948` |
| `OLLAMA_BASE_URL` / `OLLAMA_TIMEOUT_SECONDS` | Override Ollama base URL and request timeout. | `backend/pipeline/generation.py:12`, `backend/pipeline/generation.py:19` |

## 6. Known gaps / TODO / limitations

- The active code has no Dockerfile or compose file, despite old planning docs discussing Docker. Verified by `Test-Path Dockerfile`, `Test-Path docker-compose.yml`, and `Test-Path docker-compose.yaml` returning `False`.
- No Qdrant, vector embeddings, or dense retrieval are implemented in active code. Retrieval is BM25/hierarchical/deterministic scoring (`backend/pipeline/retrieval.py:167`, `backend/pipeline/retrieval.py:731`).
- Documents/chunks are stored in JSON files under chat folders, while SQLite stores users and usage events only (`backend/storage.py:25`, `backend/storage.py:29`, `backend/db.py:25`, `backend/db.py:43`).
- Payment is time-entitlement based; "2 free chats / paid max 5 chats" is not implemented in code. Current free grant/payment behavior is one entitlement window (`backend/db.py:83`, `backend/db.py:91`, `backend/db.py:125`).
- There is no Razorpay webhook route; payment routes are order creation and verification (`backend/main.py:286`, `backend/main.py:332`).
- Google auth is implemented as credential POST `/auth/google`, not an OAuth start/callback route pair (`backend/main.py:249`).
- Frontend chat always uses `chat_id: 'default'` in the current workbench (`src/components/sections/Workbench.jsx:134`, `src/components/sections/Workbench.jsx:190`).
- `npm run build` failed during audit because the sandbox could not create `dist/assets`: `Access is denied. (os error 5)`.
- `python -m py_compile ...` failed during audit because the sandbox could not write `backend\pipeline\__pycache__\...`: `Permission denied`.

## 7. Discrepancies found during audit

| Claim from old docs | Source file | Reality from code/config/command | Verdict |
| --- | --- | --- | --- |
| Backend routes are under `/api/v1/...`. | `Scope.md`, planning content | Active config/API uses `/context-forge/api` (`config.json:16`, `backend/main.py:143`). | WRONG |
| Google auth uses `/auth/google/start` and `/auth/google/callback`. | `Scope.md`, planning content | Active code exposes `POST /context-forge/api/auth/google` only (`backend/main.py:249`). | WRONG |
| Razorpay webhook endpoint exists. | `Scope.md`, planning content | Active code has `/payment/order` and `/payment/verify`, no webhook route (`backend/main.py:286`, `backend/main.py:332`, route grep output). | WRONG |
| SQLite stores users, auth metadata, billing status, chats, chat messages, documents, chunks, traces, and upload order. | `Scope.md`, planning content | SQLite has `users` and `usage_events`; documents/chunks are JSON files (`backend/db.py:25`, `backend/db.py:43`, `backend/storage.py:25`, `backend/storage.py:29`). | WRONG |
| App implements 2 free chats and paid unlock to 5 chats. | `Scope.md`, planning content | Code implements one free entitlement window and paid time extension, not chat-count billing (`backend/db.py:83`, `backend/db.py:91`, `backend/db.py:125`). | WRONG |
| Qdrant/vector store is part of MVP/current implementation. | `Scope.md`, planning content | No Qdrant dependency or vector code exists; retrieval is local BM25/hierarchical. | WRONG |
| `python-dotenv`, `python-jose`, and `authlib` are backend dependencies. | `Scope.md`, planning content | `backend/requirements.txt` contains `fastapi`, `uvicorn`, `pydantic`, `pypdf`, `python-docx`, `google-auth` only. | WRONG |
| Project has Docker/Compose strategy. | `Scope.md`, planning content | No Dockerfile or compose file exists in the audited tree. | UNVERIFIED/NOT IMPLEMENTED |
| README links active baseline docs at root. | `README.md:34` through `README.md:39` | Baseline docs are historical and now archived under `docs/archive/`. | STALE |
| README says backend reads active settings from `backend/.env`. | `README.md:91` | Backend loads root `.env`, `backend/.env`, and `backend/secrets.env` (`backend/config.py:10`, `backend/config.py:11`, `backend/config.py:12`, `backend/config.py:27`). | STALE |
| README says `JWT_SECRET` is in `backend/secrets.env.example`. | `README.md:151` | Tracked `backend/secrets.env.example` does not include `JWT_SECRET`; code still reads `JWT_SECRET` (`backend/secrets.env.example:1`, `backend/config.py:105`). | WRONG |
| README says `backend/reports/` is active runtime storage. | `README.md:207` | `backend/reports/` is gitignored generated output and was archived as historical output (`.gitignore:29`). | STALE |
| Project.md accurately describes current product shape and deploy reality. | `Project.md` | Mostly aligned with current code: `/context-forge/api`, Google auth gate, Razorpay hourly access, SQLite usage tracking, V3.1 baseline. | CONFIRMED |
| V4 is not implemented. | `V4_FUTURE.md:3` | No V4 route/version exists; active RAG versions are `v0` through `v3.1` (`backend/main.py:49`). | CONFIRMED |
| Baseline benchmark numbers are current live metrics. | `V2_BASELINE.md`, `V3_BASELINE.md`, `V3_1_BASELINE.md`, `Output.md` | They are historical tracked claims; audit did not re-run benchmarks. | STALE/UNVERIFIED |
| Generated `backend/reports/*.md` and `*.txt` are active documentation. | generated reports inventory | They are ignored generated outputs (`.gitignore:29`); archived as historical reports, not authoritative current status. | STALE |
| `backend/requirements.txt` is documentation to archive. | inventory pattern `*.txt` | It is an active dependency manifest and must remain in place. | CONFIRMED ACTIVE CONFIG |

## 8. How to run

### Standalone frontend

```powershell
npm install
npm run dev
```

Verified from `package.json:7`. Vite uses the `/context-forge/` base path (`vite.config.js:6`). The dev server port is Vite's default unless overridden; config/CORS expects `http://localhost:5173` and `http://127.0.0.1:5173` (`config.json:19`).

### Standalone backend

```powershell
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Dependencies are from `backend/requirements.txt:1` through `backend/requirements.txt:6`. Direct script mode also binds `127.0.0.1:8000` (`backend/main.py:588`).

### Integrated local run

1. Start backend on `127.0.0.1:8000`.
2. Start frontend with `npm run dev`.
3. Open:

```text
http://localhost:5173/context-forge/
```

The frontend combines `api_base_url` and `api_prefix` from `config.json` (`src/lib/api.js:4`, `src/lib/api.js:5`). With current `config.json`, same-origin deployments use `api_base_url: ""` and `/context-forge/api`; during Vite dev, empty `api_base_url` falls back to `http://localhost:8000` (`src/lib/api.js:4`, `config.json:15`, `config.json:16`).

## 9. Archive index

All active documentation is consolidated into `README.md` and this file. Historical docs and generated reports were archived under `docs/archive/`; see `docs/archive/README.md`.
