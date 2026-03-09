"""
FastAPI dependency injection for shared services.
All services are initialised once at startup via lifespan and
stored in app.state, then exposed through these dependency functions.
"""

from fastapi import Request, HTTPException
from app.core.rag import RAGService
from app.core.session_manager import SessionManager
from app.core.scoring import ScoringEngine
from app.core.llm import LLMService


def get_rag_service(request: Request) -> RAGService:
    service: RAGService = request.app.state.rag_service
    if service is None:
        raise HTTPException(status_code=503, detail="RAG service unavailable")
    return service


def get_session_manager(request: Request) -> SessionManager:
    manager: SessionManager = request.app.state.session_manager
    if manager is None:
        raise HTTPException(status_code=503, detail="Session manager unavailable")
    return manager


def get_scoring_engine(request: Request) -> ScoringEngine:
    return request.app.state.scoring_engine


def get_llm_service(request: Request) -> LLMService:
    service: LLMService = request.app.state.llm_service
    if service is None:
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    return service


def get_cases(request: Request) -> list[dict]:
    return request.app.state.cases


def get_case_index(request: Request) -> dict:
    return request.app.state.case_index