# ClinSim AI

An interactive clinical case simulator for medical resident training, powered by real MIMIC patient data, retrieval-augmented generation (RAG), and Claude.

Residents are presented with a de-identified patient case and must take a focused history, order targeted labs, and arrive at the correct diagnosis — all within resource and time limits. The system scores performance and provides a structured debrief.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Data Pipeline](#data-pipeline)
- [Case Generation](#case-generation)
- [Scoring](#scoring)
- [Development](#development)
- [Known Limitations](#known-limitations)

---

## Overview

ClinSim AI is built around three workstreams:

1. **Foundation** — Download the MIMIC dataset from HuggingFace, parse discharge summaries with Claude, build a FAISS vector index for RAG
2. **Simulation** — FastAPI backend manages sessions, streams patient dialogue via SSE, scores diagnoses against ICD-9 codes
3. **Frontend** — Next.js 15 App Router UI with real-time patient chat, lab ordering, and a results debrief screen

The frontend can run in **mock mode** (no backend required, uses a static JSON session) or **real mode** (connected to the live FastAPI backend).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic, Uvicorn |
| LLM | Claude (`claude-opus-4-5-20251101`) via Anthropic API |
| RAG | FAISS + `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Dataset | MIMIC (HuggingFace: `bavehackathon/2026-healthcare-ai`) |
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Package manager | `uv` (backend), `npm` (frontend) |

---

## Project Structure

```
clinsim_ai/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # FastAPI endpoints
│   │   │   ├── cases.py       # GET /api/cases
│   │   │   ├── sessions.py    # Session lifecycle + chat + labs + diagnose
│   │   │   ├── diagnoses.py   # ICD-9 autocomplete search
│   │   │   ├── generation.py  # Case generation jobs
│   │   │   └── health.py      # Health check
│   │   ├── core/
│   │   │   ├── llm.py         # LLMService (Anthropic + OpenAI)
│   │   │   ├── rag.py         # RAGService (FAISS retrieval)
│   │   │   ├── session_manager.py  # Session CRUD + resource limits
│   │   │   └── scoring.py     # ICD-9 matched scoring engine
│   │   ├── data/
│   │   │   ├── loader.py      # HuggingFace dataset download + pandas
│   │   │   └── parser.py      # LLM-powered discharge summary parser
│   │   ├── generation/        # Case variation engine
│   │   │   ├── template_extractor.py
│   │   │   ├── variation_generator.py
│   │   │   └── clinical_validator.py
│   │   ├── rag/
│   │   │   ├── chunker.py     # Case -> text chunks
│   │   │   └── indexer.py     # FAISS index builder
│   │   ├── prompts/           # All LLM prompt templates
│   │   ├── cli/
│   │   │   ├── build_foundation.py   # One-time data pipeline
│   │   │   └── generate_cases.py     # Case variation CLI
│   │   ├── main.py            # FastAPI app + lifespan startup
│   │   ├── dependencies.py    # FastAPI dependency injection
│   │   ├── models.py          # Pydantic schemas (Case, Session, etc.)
│   │   └── config.py          # Settings (reads from .env)
│   ├── tests/
│   │   └── integration/       # End-to-end integration tests
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/               # Next.js App Router pages
│       │   ├── page.tsx       # Case library (home)
│       │   ├── session/[sessionId]/  # Active simulation
│       │   └── results/[sessionId]/  # Debrief + score
│       ├── components/
│       │   ├── actions/       # ActionBar, DiagnosisModal
│       │   ├── clinical/      # VitalsPanel, LabsPanel, LabOrderModal
│       │   ├── patient/       # PatientChat
│       │   └── results/       # ScoreCard, PathComparison
│       ├── hooks/
│       │   ├── useSession.ts  # Session state + lab/diagnosis actions
│       │   └── usePatientChat.ts  # Chat with streaming animation
│       └── lib/
│           ├── api.ts         # Real + mock ApiClient implementation
│           ├── mock-api.ts    # Static mock for frontend dev
│           └── types.ts       # Shared TypeScript types
├── data/                      # Generated artifacts (gitignored)
│   ├── cases.json
│   ├── chunks.json
│   └── faiss.index
└── docs/                      # Specs, plans, deployment guide
```

---

## How It Works

### Simulation flow

```
User selects case
  -> POST /api/sessions              (creates session)
  -> POST /api/sessions/{id}/chat    (SSE stream, patient responds via Claude + RAG)
  -> POST /api/sessions/{id}/labs    (returns lab result from case data)
  -> POST /api/sessions/{id}/exam    (returns physical exam findings)
  -> POST /api/sessions/{id}/diagnose  (submits ICD-9 diagnosis, triggers scoring)
  -> GET  /api/sessions/{id}/results   (returns score breakdown + debrief)
```

### RAG grounding

Each case is chunked into typed segments (`presenting_complaint`, `hpi`, `physical_exam`, `labs`, `medications`, `hospital_course`, `diagnosis`). When a trainee asks a question, the question type is classified and the most relevant chunks are retrieved from FAISS and injected into the patient dialogue prompt — so Claude responds only with information the case contains.

### Scoring

Scores are ICD-9 code matched:

| Component | Max points |
|---|---|
| Primary diagnosis (exact ICD-9 match) | 40 |
| Primary diagnosis (category match, first 3 digits) | 20 |
| Differentials | 30 |
| Efficiency (resource usage) | 30 |
| Time bonus (under 5 min) | 20 |
| **Total maximum** | **120** |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- `uv` — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- An Anthropic API key

### 1. Clone and install

```bash
git clone https://github.com/hippocratik/clinsim_ai.git
cd clinsim_ai

# Backend
cd backend && uv sync --all-extras

# Frontend
cd ../frontend && npm install
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — set ANTHROPIC_API_KEY at minimum
```

### 3. Build the data artifacts (one-time)

```bash
cd backend
uv run python -m app.cli.build_foundation --num-cases 20
```

This downloads the MIMIC dataset, parses cases with Claude, and builds the FAISS index. Artifacts are saved to `data/`. See the [Data Pipeline](#data-pipeline) section for details.

### 4. Start the backend

```bash
cd backend
uv run uvicorn app.main:app --reload
# API at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### 5. Start the frontend

```bash
cd frontend

# Mock mode (no backend needed — default):
npm run dev

# Real mode (against live backend):
echo "NEXT_PUBLIC_API_MODE=real" >> .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" >> .env.local
npm run dev
```

Frontend at `http://localhost:3000`.

---

## Configuration

All backend settings are read from `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | _(required)_ | Anthropic API key |
| `OPENAI_API_KEY` | `""` | OpenAI API key (optional) |
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `LLM_MODEL` | _(provider default)_ | Override model (e.g. `claude-opus-4-5-20251101`) |
| `LLM_MAX_TOKENS` | `1024` | Max tokens per LLM response |
| `CASES_PATH` | `data/cases.json` | Path to parsed cases file |
| `CHUNKS_PATH` | `data/chunks.json` | Path to RAG chunks file |
| `FAISS_INDEX_PATH` | `data/faiss.index` | Path to FAISS index |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `RAG_TOP_K` | `5` | Chunks retrieved per query |
| `SESSION_TIMEOUT_MINUTES` | `60` | Session auto-expiry |
| `DEFAULT_RESOURCE_BUDGET` | `100` | Default resource budget per session |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

Frontend environment variables (`frontend/.env.local`):

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_MODE` | `mock` | `mock` or `real` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL |

---

## API Reference

Full interactive docs at `http://localhost:8000/docs` when the backend is running.

### Cases

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/cases` | List cases (filter: `?difficulty=`, `?specialty=`, `?is_generated=`) |
| `GET` | `/api/cases/{case_id}` | Case metadata — diagnoses are NOT returned |

### Sessions

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/sessions` | Create a session (`{ case_id }`) |
| `GET` | `/api/sessions/{id}` | Get session state |
| `POST` | `/api/sessions/{id}/chat` | Send message — SSE stream response |
| `POST` | `/api/sessions/{id}/labs` | Order a lab (`{ lab_name }`) |
| `POST` | `/api/sessions/{id}/exam` | Perform exam (`{ system }`) |
| `POST` | `/api/sessions/{id}/diagnose` | Submit diagnosis and complete session |
| `GET` | `/api/sessions/{id}/results` | Get score and debrief |

### Diagnoses

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/diagnoses/search?q=` | ICD-9 autocomplete |

### Generation

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/generate` | Start case generation job |
| `GET` | `/api/generate/{job_id}` | Poll job status |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health — returns RAG/LLM status and case count |

---

## Data Pipeline

The foundation pipeline runs once before the server starts to produce the static data artifacts loaded at startup.

```bash
cd backend
uv run python -m app.cli.build_foundation --num-cases 20
```

**Steps:**

1. Downloads MIMIC dataset from HuggingFace (`bavehackathon/2026-healthcare-ai`) via `snapshot_download()` + pandas
2. For each case, calls Claude to parse the discharge summary into structured JSON
3. Chunks each case into typed text segments
4. Builds a FAISS vector index using `all-MiniLM-L6-v2` embeddings
5. Saves `data/cases.json`, `data/chunks.json`, `data/faiss.index`

**Cost and time estimates:**

| Cases | Approx. API cost | Approx. time |
|---|---|---|
| 20 | $0.20–0.30 | ~2 min |
| 200 | $2–3 | ~20 min |
| 2000 | $20–30 | ~3–6 hours |

The `data/` directory is gitignored — artifacts must be generated locally or on the server. See the [Deployment Guide](docs/deployment.md).

---

## Case Generation

Generate additional case variations from existing source cases:

```bash
cd backend
uv run python -m app.cli.generate_cases \
  --source-case case_001 \
  --count 3 \
  --dry-run      # remove --dry-run to save
```

The pipeline:
1. Extracts a `ClinicalTemplate` from the source case (LLM)
2. Generates a variation grounded in RAG-retrieved similar cases (LLM)
3. Validates with rule-based checks (vital ranges, lab ranges, demographics) + optional LLM plausibility check
4. Saves valid cases to `data/cases.json` — available immediately via the API

Generated cases are marked `is_generated: true`.

---

## Scoring

The `ScoringEngine` compares submitted ICD-9 codes against ground-truth diagnoses from the MIMIC case:

- **Primary diagnosis** — exact ICD-9 match = 40 pts; 3-digit category match = 20 pts; no match = 0 pts
- **Differentials** — up to 30 pts, proportional to matched ICD-9 codes (max 3 considered)
- **Efficiency** — 30 pts minus penalties: excess questions (>8, -2 each), labs (>4, -3 each), exams (>2, -2 each)
- **Time bonus** — 20 pts for under 5 min; 0 pts over 15 min; linear between

Feedback is a list of human-readable strings included in the results response alongside the numeric breakdown.

---

## Development

### Running tests

```bash
cd backend
uv run pytest tests/ -v
```

### Conventions

- **Package manager:** `uv` for Python (never `pip`), `npm` for frontend
- **Commits:** conventional commits — `feat:`, `fix:`, `chore:`, `docs:`
- **Branching:** always use a git worktree (`.worktrees/<branch>`), never commit directly to `main`
- **TDD:** write failing test first, implement, then verify passing
- **API key:** store in `backend/.env` only — never pass on the command line or commit

---

## Known Limitations

- **In-memory state** — sessions, generated cases, and the case index are held in RAM. A server restart clears all active sessions. No database persistence.
- **Single-worker only** — `app.state` is process-local. Use `--workers 1` in production. Multi-worker support requires replacing in-memory stores with Redis or a shared backend.
- **RAG optional** — if the FAISS index is missing or `torch`/`sentence-transformers` fail to load, chat falls back to minimal context (presenting complaint + HPI). Diagnostic quality will be lower.
- **No authentication** — no user auth or session ownership. Any client with a session ID can access that session.
- **Case list returns minimal data** — `GET /api/cases` and `GET /api/cases/{id}` return only presenting complaint, difficulty, and specialties to avoid spoiling diagnoses. Full case fields (demographics, vitals, labs) are only available within an active session context.
