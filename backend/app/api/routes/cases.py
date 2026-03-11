from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.dependencies import get_cases, get_case_index
from app.models import Demographics, PhysicalExam, LabResult

router = APIRouter(prefix="/api/cases", tags=["cases"])


class CaseListItem(BaseModel):
    case_id: str
    difficulty: str
    specialties: list[str]
    presenting_complaint: str
    is_generated: bool


class CaseDetailSafe(BaseModel):
    """
    Session-safe case detail payload.
    Intentionally excludes diagnoses and discharge summary.
    """
    case_id: str
    subject_id: int
    hadm_id: int
    demographics: Demographics
    presenting_complaint: str
    hpi: str
    past_medical_history: list[str]
    medications: list[str]
    allergies: list[str]
    physical_exam: PhysicalExam
    available_labs: list[LabResult]
    difficulty: str
    specialties: list[str]
    source_case_id: Optional[str] = None
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


@router.get("/{case_id}/detail", response_model=CaseDetailSafe)
def get_case_detail_safe(
    case_id: str,
    case_index: dict = Depends(get_case_index),
):
    """Get session-safe case detail (does NOT reveal diagnoses)."""
    case = case_index.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    return CaseDetailSafe(
        case_id=case["case_id"],
        subject_id=case.get("subject_id", 0),
        hadm_id=case.get("hadm_id", 0),
        demographics=case.get(
            "demographics",
            {"age": 0, "gender": "M", "admission_type": "Unknown"},
        ),
        presenting_complaint=case.get("presenting_complaint", ""),
        hpi=case.get("hpi", ""),
        past_medical_history=case.get("past_medical_history", []),
        medications=case.get("medications", []),
        allergies=case.get("allergies", []),
        physical_exam=case.get(
            "physical_exam",
            {
                "vitals": {
                    "heart_rate": None,
                    "blood_pressure": None,
                    "respiratory_rate": None,
                    "temperature": None,
                    "spo2": None,
                },
                "findings": "",
            },
        ),
        available_labs=case.get("available_labs", []),
        difficulty=case.get("difficulty", "medium"),
        specialties=case.get("specialties", []),
        source_case_id=case.get("source_case_id"),
        is_generated=case.get("is_generated", False),
    )