# ContextForge

![ContextForge overview](./images/Overlay.png)

ContextForge is a React/Vite + FastAPI local RAG workbench for comparing versioned retrieval behavior over the same uploaded corpus.

The current implementation supports:

- file ingestion for `.md`, `.mdx`, `.txt`, `.pdf`, and `.docx`
- versioned retrieval paths: `v0`, `v1`, `v2`, `v3`, `v3.1`
- deterministic extraction/synthesis answer paths
- Ollama-backed generation
- cited answers and retrieval metadata
- Google credential auth when `backend/secrets.env` is configured
- Razorpay order + payment verification when payment secrets are configured
- SQLite user/usage tracking

An earlier implementation-status snapshot (endpoint inventory, config values, benchmark notes, audit findings) is archived, now outdated, at [docs/archive/Project-Status.md](./docs/archive/Project-Status.md).

## Run Contract

### Standalone Backend

```powershell
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The backend API is mounted under the configured prefix. With the checked-in `config.json`, the prefix is:

```text
/context-forge/api
```

FastAPI docs are configured at:

```text
/context-forge/api/docs
```

### Standalone Frontend

```powershell
cd frontend
npm install
npm run dev
```

The Vite app is built with:

```text
/context-forge/
```

Open the local app at:

```text
http://localhost:5173/context-forge/
```

### Integrated Local Run

1. Start the backend on `127.0.0.1:8000`.
2. Start the frontend with `npm run dev`.
3. Open `http://localhost:5173/context-forge/`.

In dev mode, the frontend API client falls back to `http://localhost:8000` when `api_base_url` is empty.

## Docker

```powershell
copy .env.example .env
docker compose up -d --build
```

Serves the built frontend and API together at `http://localhost:8000/context-forge/`. The
container reaches an Ollama instance running on the host via `OLLAMA_BASE_URL=http://host.docker.internal:11434`
in `.env`.

## Inference Backend

The default generation backend is Ollama. The checked-in config points to:

```text
http://localhost:11434
```

Default model:

```text
qwen3:4b-instruct
```

Some extraction and synthesis queries use deterministic backend paths when the frontend sends provider `auto`; forced Ollama mode sends the request to the local Ollama API.

## Auth And Payment

Local mode is used when `backend/secrets.env` is absent or auth is not fully configured.

Production-like mode requires secrets in `backend/secrets.env`, based on [backend/secrets.env.example](./backend/secrets.env.example). Do not commit real secrets.

Current behavior:

- Google auth is implemented as `POST /context-forge/api/auth/google`.
- Razorpay order creation is `POST /context-forge/api/payment/order`.
- Razorpay payment verification is `POST /context-forge/api/payment/verify`.
- There is no Razorpay webhook endpoint in the current code.

## Documentation

[README.md](./README.md) is the current source of truth.

Historical plans, baselines, benchmark notes, generated reports, and the (now outdated) implementation-status snapshot are archived under [docs/archive/](./docs/archive/).
