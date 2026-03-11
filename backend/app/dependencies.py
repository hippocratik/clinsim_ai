"""
FastAPI dependency injection for shared services.
All services are initialised once at startup via lifespan and
stored in app.state, then exposed through these dependency functions.
"""

from typing import TYPE_CHECKING, Optional
from fastapi import Request, HTTPException
from app.core.session_manager import SessionManager

if TYPE_CHECKING:
    from app.core.rag import RAGService
from app.core.scoring import ScoringEngine
from app.core.llm import LLMService


def get_rag_service(request: Request) -> "RAGService":
    service: RAGService = request.app.state.rag_service
    if service is None:
        raise HTTPException(status_code=503, detail="RAG service unavailable")
    return service


def get_rag_service_optional(request: Request) -> Optional["RAGService"]:
    """Return RAG service if available, else None. Use for chat when RAG is disabled (e.g. torch not loaded)."""
    return getattr(request.app.state, "rag_service", None)


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