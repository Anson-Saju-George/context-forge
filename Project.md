# ContextForge

## Project Snapshot

ContextForge is a local-first RAG workbench for comparing retrieval architectures over the same uploaded corpus.

The product is built around one concrete idea:

- keep the document set fixed
- run the same questions through multiple retrieval versions
- inspect how answer quality changes as retrieval gets stricter, better balanced, and more evidence-driven

This is not a generic chatbot project. It is a retrieval systems workbench.

## What It Actually Ships

Current shipped scope:

- React + Vite frontend
- FastAPI backend
- document upload for `.md`, `.mdx`, `.txt`, `.pdf`, `.docx`
- local chat/document storage
- selectable retrieval versions: `v0`, `v1`, `v2`, `v3`, `v3.1`
- deterministic answer path for benchmark-style synthesis/extraction
- Ollama answer path for model-sensitive runs
- cited answers with retrieval metadata
- benchmark runner for side-by-side version comparison
- Google auth gate in production mode
- Razorpay hourly access flow
- SQLite-backed user and usage tracking
- configurable frontend mount path such as `/rag/`

## Core Product Shape

The UI is intentionally split into two layers:

1. Overlay
   - positions the product as a retrieval-evolution workbench
   - enforces auth/payment in production mode
   - lets the user choose the active RAG version before entering

2. Workbench
   - upload documents
   - ingest and clear corpus
   - run the same prompt against different retrieval versions
   - inspect citations, retrieval traces, and response behavior

## Retrieval Version Progression

The system is organized as an explicit retrieval maturity ladder.

### V0

- similarity toy baseline
- single-stage chunk retrieval
- useful mainly as a failure-mode reference

### V1

- first BM25/hierarchical retrieval baseline
- stronger exact-term recall
- still prone to right-topic / wrong-evidence behavior

### V2

- routed retrieval milestone
- document-balanced synthesis
- more stable all-document comparisons

### V3

- benchmark-focused production-style baseline
- cached retrieval features
- stronger source coverage
- cleaner mechanism extraction

### V3.1

- evidence-first clean baseline
- best local mechanism recall
- stronger evidence discipline and lower hallucination freedom

## Auth, Access, and Billing Model

The app has two runtime modes.

### Local mode

When `backend/secrets.env` does not exist:

- no auth wall
- no payment wall
- direct local use

### Production mode

When `backend/secrets.env` exists:

- Google auth can be enabled
- Razorpay payment can be enabled
- usage is tracked in SQLite

Current access logic:

- first successful user login gets `1 hour free`
- after that, access is extended in `1 hour` windows
- standard paid window is `Rs 20 / hour`
- emails in `ADMIN_EMAILS` have unlimited access

## Usage Tracking

Usage is tracked server-side in SQLite, not only in the browser.

Stored state includes:

- user identity
- free-grant status
- entitlement expiry timestamp
- payment totals
- payment count
- query count
- ingest count
- uploaded chunk count
- usage event history

The active timer is absolute-time based, not heartbeat based. If a user loses internet, entitlement still remains correct because expiry is stored on the server.

## Current Storage Model

Runtime data is kept local and gitignored.

Important paths:

- `data/contextforge.db` - SQLite usage/auth database
- `data/chats/` - shortened local chat/document storage
- `backend/reports/` - benchmark and smoke outputs

This keeps the demo practical without pretending the app is already multi-tenant cloud infrastructure.

## Backend Shape

Main backend files:

- `backend/main.py` - API surface and request flow
- `backend/config.py` - config and env resolution
- `backend/auth.py` - Google auth, session, entitlement logic
- `backend/db.py` - SQLite persistence and usage tracking
- `backend/models.py` - API/data models
- `backend/storage.py` - local document storage helpers
- `backend/ultimate_run.py` - version-by-version benchmark runner
- `backend/pipeline/` - retrieval/generation implementations per version

## Frontend Shape

Main frontend concerns:

- route-aware Vite mount path
- overlay gating and version selection
- Google login flow
- Razorpay payment trigger
- upload/ingest workflow
- version-aware chat workbench
- retrieval/answer inspection

The frontend is intentionally minimal. It does not try to be a large admin product.

## Benchmark Philosophy

The benchmark focus is not “which model sounds smartest”.

The benchmark focus is:

- multi-document coverage
- mechanism extraction fidelity
- evidence discipline
- source balance
- retrieval contamination resistance
- model sensitivity after retrieval matures

That is why the app supports both:

- deterministic benchmark mode
- Ollama-driven model comparison mode

## Current Technical Positioning

This project is strongest when described as:

- retrieval systems engineering
- local RAG benchmarking
- evidence-aware answer generation
- production-style auth/payment gating for a demo tool
- versioned retrieval architecture comparison

It should not be described as:

- an all-purpose AI platform
- a full enterprise knowledge system
- a universal RAG framework

## Deploy Reality

The current deploy target is a controlled demo environment:

- frontend mounted under a configured path
- backend serving versioned RAG APIs
- Google auth and Razorpay enabled through `backend/secrets.env`
- Qwen-based default Ollama generation policy enforced through backend config

That is a coherent deployment story for the code as it exists today.

## Near-Term Future

The next reasonable step is not more surface area. It is tightening the system around what already works:

- better benchmark reference outputs
- clearer admin usage visibility
- production deployment hardening
- cleaner reporting for version-by-version runs
- future `v4` only when it introduces a real retrieval gain
