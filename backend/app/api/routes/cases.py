from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.dependencies import get_cases, get_case_index
from app.models import Case

router = APIRouter(prefix="/api/cases", tags=["cases"])


class CaseListItem(BaseModel):
    case_id: str
    difficulty: str
    specialties: list[str]
    presenting_complaint: str
    is_generated: bool


@router.get("", response_model=list[CaseListItem])
def list_cases(
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    is_generated: Optional[bool] = Query(None, description="Filter by generated flag"),
    cases: list[dict] = Depends(get_cases),
):
    """List all cases with optional filters."""
    results = cases

    if difficulty:
        results = [c for c in results if c.get("difficulty") == difficulty]
    if specialty:
        results = [c for c in results if specialty in c.get("specialties", [])]
    if is_generated is not None:
        results = [c for c in results if c.get("is_generated", False) == is_generated]

    return [
        CaseListItem(
            case_id=c["case_id"],
            difficulty=c["difficulty"],
            specialties=c.get("specialties", []),
            presenting_complaint=c["presenting_complaint"],
            is_generated=c.get("is_generated", False),
        )
        for c in results
    ]


@router.get("/{case_id}", response_model=CaseListItem)
def get_case(
    case_id: str,
    case_index: dict = Depends(get_case_index),
):
    """Get metadata for a specific case (does NOT reveal diagnoses)."""
    case = case_index.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    return CaseListItem(
        case_id=case["case_id"],
        difficulty=case["difficulty"],
        specialties=case.get("specialties", []),
        presenting_complaint=case["presenting_complaint"],
        is_generated=case.get("is_generated", False),
    )