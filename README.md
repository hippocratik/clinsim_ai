# ClinSim AI

An interactive clinical case simulator for medical resident training, powered by real patient data, retrieval-augmented generation (RAG), and Claude.

Residents are presented with a de-identified patient case and must take a focused history, order targeted labs, and arrive at the correct diagnosis — all within resource and time limits. The system scores performance and provides a structured debrief.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic |
| LLM | Claude (`claude-opus-4-5-20251101`) via Anthropic API |
| RAG | FAISS + `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Package manager | `uv` (backend), `npm` (frontend) |

---

## Dataset

ClinSim AI uses the **MIMIC** dataset hosted on HuggingFace (`bavehackathon/2026-healthcare-ai`). It contains de-identified clinical cases including discharge summaries, diagnoses (ICD-9 coded), lab results, and prescriptions derived from real hospital admissions.

Before running the application, a one-time data pipeline must be executed to download the dataset, parse discharge summaries with Claude, and build a FAISS vector index. See the [Deployment Guide](docs/deployment.md) for details.

---

## Getting Started

```bash
# Install backend dependencies
cd backend && uv sync --all-extras

# Run the foundation pipeline (one-time)
uv run python -m app.cli.build_foundation --num-cases 20

# Start the backend
uv run uvicorn app.main:app --reload

# Start the frontend
cd frontend && npm install && npm run dev
```

Store your `ANTHROPIC_API_KEY` in `backend/.env` — never pass it on the command line.

For full deployment instructions on a VM server, see [docs/deployment.md](docs/deployment.md).

---

## License

MIT
