from fastapi import APIRouter, Request
from datetime import datetime

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request):
    """Basic health check — verifies services are loaded."""
    rag_ok = getattr(request.app.state, "rag_service", None) is not None
    llm_ok = getattr(request.app.state, "llm_service", None) is not None
    cases_count = len(getattr(request.app.state, "cases", []))

    return {
        "status": "ok" if (rag_ok and llm_ok) else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "rag": "ok" if rag_ok else "unavailable",
            "llm": "ok" if llm_ok else "unavailable",
            "cases_loaded": cases_count,
        },
    }