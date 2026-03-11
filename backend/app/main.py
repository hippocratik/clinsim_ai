import json
import faiss
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
settings = get_settings()
from app.core.session_manager import SessionManager
from app.core.scoring import ScoringEngine
from app.core.llm import LLMProvider, LLMService
from app.api.routes import cases, sessions, diagnoses, health, generation, labs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all services at startup; clean up on shutdown."""
    print("Starting ClinSim AI backend...")

    # Load cases
    cases_path = Path(settings.cases_path)
    if cases_path.exists():
        with open(cases_path) as f:
            data = json.load(f)
        # Handle both list and dict formats
        if isinstance(data, list):
            case_list = data
        elif isinstance(data, dict):
            case_list = list(data.values())
        else:
            case_list = []
        print(f"  ✓ Loaded {len(case_list)} cases from {cases_path}")
    else:
        case_list = []
        print(f"  ⚠ cases.json not found at {cases_path} — using empty list")

    app.state.cases = case_list
    app.state.case_index = {c["case_id"]: c for c in case_list}
    app.state.generation_jobs = {}

    # Build ICD-9 database from loaded cases for autocomplete
    icd9_db = {}
    for case in case_list:
        for diag in case.get("diagnoses", []):
            code = diag.get("icd9_code", "").strip()
            desc = diag.get("description", "").strip()
            if code and desc and code not in icd9_db:
                icd9_db[code] = desc
    app.state.icd9_db = icd9_db
    print(f"  ✓ Loaded {len(icd9_db)} ICD-9 codes from cases")

    # Load lab dictionary for /api/labs endpoint
    lab_dict_path = Path(settings.lab_dictionary_path)
    if lab_dict_path.exists():
        with open(lab_dict_path) as f:
            app.state.lab_dictionary = json.load(f)
        print(f"  ✓ Loaded {len(app.state.lab_dictionary)} lab items from {lab_dict_path}")
    else:
        app.state.lab_dictionary = []
        print(f"  ⚠ lab_dictionary.json not found at {lab_dict_path} — labs endpoint will return empty")

    # Load chunks
    chunks_path = Path(settings.chunks_path)
    if chunks_path.exists():
        with open(chunks_path) as f:
            chunks: list[dict] = json.load(f)
        print(f"  ✓ Loaded {len(chunks)} chunks from {chunks_path}")
    else:
        chunks = []
        print(f"  ⚠ chunks.json not found at {chunks_path} — using empty list")

    # Load FAISS index and RAG only when index exists (avoids loading torch/sentence_transformers otherwise).
    # If torch/sentence_transformers fail to load (e.g. WinError 1114 on Windows), RAG is disabled but app still starts.
    faiss_path = Path(settings.faiss_index_path)
    if faiss_path.exists() and chunks:
        try:
            from app.core.rag import RAGService
            faiss_index = faiss.read_index(str(faiss_path))
            rag = RAGService(faiss_index, chunks, settings.embedding_model)
            print(f"  ✓ RAG service ready (index: {faiss_path})")
        except Exception as e:
            rag = None
            print(f"  ⚠ RAG disabled (failed to load: {e})")
    else:
        rag = None
        print(f"  ⚠ FAISS index not found at {faiss_path} — RAG disabled")

    app.state.rag_service = rag
    app.state.session_manager = SessionManager(
        session_timeout_minutes=settings.session_timeout_minutes
    )
    app.state.scoring_engine = ScoringEngine()
    app.state.llm_service = LLMService(
        provider=LLMProvider(settings.llm_provider),
        anthropic_api_key=settings.anthropic_api_key,
    )

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
    app.include_router(generation.router)
    app.include_router(labs.router)

    return app


app = create_app()