import json
import faiss
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.rag import RAGService
from app.core.session_manager import SessionManager
from app.core.scoring import ScoringEngine
from app.core.llm import LLMService
from app.api.routes import cases, sessions, diagnoses, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all services at startup; clean up on shutdown."""
    print("Starting ClinSim AI backend...")

    # Load cases
    cases_path = Path(settings.cases_path)
    if cases_path.exists():
        with open(cases_path) as f:
            case_list: list[dict] = json.load(f)
        print(f"  ✓ Loaded {len(case_list)} cases from {cases_path}")
    else:
        case_list = []
        print(f"  ⚠ cases.json not found at {cases_path} — using empty list")

    app.state.cases = case_list
    app.state.case_index = {c["case_id"]: c for c in case_list}

    # Load chunks
    chunks_path = Path(settings.chunks_path)
    if chunks_path.exists():
        with open(chunks_path) as f:
            chunks: list[dict] = json.load(f)
        print(f"  ✓ Loaded {len(chunks)} chunks from {chunks_path}")
    else:
        chunks = []
        print(f"  ⚠ chunks.json not found at {chunks_path} — using empty list")

    # Load FAISS index
    faiss_path = Path(settings.faiss_index_path)
    if faiss_path.exists() and chunks:
        faiss_index = faiss.read_index(str(faiss_path))
        rag = RAGService(faiss_index, chunks, settings.embedding_model)
        print(f"  ✓ RAG service ready (index: {faiss_path})")
    else:
        rag = None
        print(f"  ⚠ FAISS index not found at {faiss_path} — RAG disabled")

    app.state.rag_service = rag
    app.state.session_manager = SessionManager()
    app.state.scoring_engine = ScoringEngine()
    app.state.llm_service = LLMService()

    print("  ✓ Session manager ready")
    print("  ✓ Scoring engine ready")
    print("  ✓ LLM service ready")
    print("ClinSim AI backend started.\n")

    yield

    print("Shutting down ClinSim AI backend...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ClinSim AI",
        description="Interactive clinical case simulator for medical resident training.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(cases.router)
    app.include_router(sessions.router)
    app.include_router(diagnoses.router)

    return app


app = create_app()