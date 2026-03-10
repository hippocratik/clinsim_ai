import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.dependencies import (
    get_rag_service, get_session_manager, get_scoring_engine,
    get_llm_service, get_case_index,
)
from app.core.rag import RAGService
from app.core.session_manager import SessionManager, SessionStatus
from app.core.scoring import ScoringEngine
from app.core.llm import LLMService
from app.models import Case
from app.prompts.patient_dialogue import (
    PATIENT_SYSTEM_PROMPT, build_patient_prompt, classify_question
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# ── Request / Response schemas ──────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    case_id: str


class CreateSessionResponse(BaseModel):
    session_id: str
    case_id: str
    status: str
    started_at: datetime


class ChatRequest(BaseModel):
    message: str


class LabRequest(BaseModel):
    lab_name: str


class ExamRequest(BaseModel):
    system: str


class DiagnoseRequest(BaseModel):
    primary_diagnosis: str
    differentials: list[str] = []


class SessionStateResponse(BaseModel):
    session_id: str
    case_id: str
    status: str
    question_count: int
    lab_count: int
    exam_count: int
    max_questions: int
    max_labs: int
    max_exams: int
    elapsed_seconds: float
    chat_history: list[dict]
    labs_ordered: list[dict]
    exams_performed: list[dict]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _session_to_state(session) -> SessionStateResponse:
    return SessionStateResponse(
        session_id=session.session_id,
        case_id=session.case_id,
        status=session.status.value,
        question_count=session.question_count,
        lab_count=session.lab_count,
        exam_count=session.exam_count,
        max_questions=session.max_questions,
        max_labs=session.max_labs,
        max_exams=session.max_exams,
        elapsed_seconds=session.elapsed_seconds,
        chat_history=[
            {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
            for m in session.chat_history
        ],
        labs_ordered=[
            {"lab_name": l.lab_name, "result": l.result, "ordered_at": l.ordered_at.isoformat()}
            for l in session.labs_ordered
        ],
        exams_performed=[
            {"system": e.system, "findings": e.findings, "performed_at": e.performed_at.isoformat()}
            for e in session.exams_performed
        ],
    )


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=CreateSessionResponse)
def create_session(
    body: CreateSessionRequest,
    case_index: dict = Depends(get_case_index),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Create a new simulation session for a given case."""
    if body.case_id not in case_index:
        raise HTTPException(status_code=404, detail=f"Case '{body.case_id}' not found")

    session = session_manager.create_session(body.case_id)
    return CreateSessionResponse(
        session_id=session.session_id,
        case_id=session.case_id,
        status=session.status.value,
        started_at=session.started_at,
    )


@router.get("/{session_id}", response_model=SessionStateResponse)
def get_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Get the current state of a session."""
    try:
        session = session_manager.get_session_or_raise(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return _session_to_state(session)


@router.post("/{session_id}/chat")
async def chat(
    session_id: str,
    body: ChatRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    rag_service: RAGService = Depends(get_rag_service),
    llm_service: LLMService = Depends(get_llm_service),
    case_index: dict = Depends(get_case_index),
):
    """
    Send a message to the patient — returns Server-Sent Events stream.
    Each event is: data: <json>\n\n
    """
    try:
        session = session_manager.get_session_or_raise(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.can_ask_question():
        raise HTTPException(
            status_code=400,
            detail=f"Question limit reached ({session.max_questions}) or session not active"
        )

    # Record trainee message
    session_manager.add_chat_message(session_id, "trainee", body.message)

    # RAG retrieval — use question classifier to target relevant chunk types
    chunk_types = classify_question(body.message)
    chunks = rag_service.retrieve(
        query=body.message,
        case_id=session.case_id,
        chunk_types=chunk_types,
        top_k=4,
    )

    # Build prompt
    patient_prompt = build_patient_prompt(
        chunks=chunks,
        chat_history=session.chat_history[:-1],  # exclude the message we just added
        trainee_question=body.message,
    )

    async def event_generator():
        full_response = []
        async for token in llm_service.generate_stream(
            system_prompt=PATIENT_SYSTEM_PROMPT,
            user_prompt=patient_prompt,
            max_tokens=300,
        ):
            full_response.append(token)
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Save completed response
        complete_text = "".join(full_response)
        session_manager.add_chat_message(session_id, "patient", complete_text)
        yield f"data: {json.dumps({'done': True, 'full_response': complete_text})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{session_id}/labs")
def order_lab(
    session_id: str,
    body: LabRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    case_index: dict = Depends(get_case_index),
):
    """Order a lab test. Returns the result if available in the case."""
    try:
        session = session_manager.get_session_or_raise(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.can_order_lab():
        raise HTTPException(
            status_code=400,
            detail=f"Lab limit reached ({session.max_labs}) or session not active"
        )

    # Look up lab result from case
    case_data = case_index.get(session.case_id, {})
    available_labs = {
        lab["lab_name"].lower(): lab
        for lab in case_data.get("available_labs", [])
    }
    match = available_labs.get(body.lab_name.lower())
    result_str = (
        f"{match['value']} {match['unit']} ({match['flag']})"
        if match else "Lab not available in this case"
    )

    lab = session_manager.record_lab_order(session_id, body.lab_name, result_str)
    return {"lab_name": lab.lab_name, "result": lab.result, "ordered_at": lab.ordered_at.isoformat()}


@router.post("/{session_id}/exam")
def perform_exam(
    session_id: str,
    body: ExamRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    case_index: dict = Depends(get_case_index),
):
    """Perform a physical exam on a system. Returns findings from the case."""
    try:
        session = session_manager.get_session_or_raise(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.can_perform_exam():
        raise HTTPException(
            status_code=400,
            detail=f"Exam limit reached ({session.max_exams}) or session not active"
        )

    case_data = case_index.get(session.case_id, {})
    findings = case_data.get("physical_exam", {}).get("findings", "No specific findings documented.")

    exam = session_manager.record_exam(session_id, body.system, findings)
    return {
        "system": exam.system,
        "findings": exam.findings,
        "performed_at": exam.performed_at.isoformat(),
    }


@router.post("/{session_id}/diagnose")
def submit_diagnosis(
    session_id: str,
    body: DiagnoseRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    scoring_engine: ScoringEngine = Depends(get_scoring_engine),
    case_index: dict = Depends(get_case_index),
):
    """Submit a diagnosis — completes the session and returns the score."""
    try:
        session = session_manager.get_session_or_raise(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")

    session_manager.submit_diagnosis(session_id, body.primary_diagnosis, body.differentials)

    # Score immediately
    case_data = case_index.get(session.case_id)
    if case_data:
        from app.models import Case
        case = Case(**case_data)
        score = scoring_engine.score_session(session, case)
        return {
            "session_id": session_id,
            "status": session.status.value,
            "score": {
                "primary_diagnosis": score.primary_diagnosis,
                "differential": score.differential,
                "efficiency": score.efficiency,
                "time_bonus": score.time_bonus,
                "total": score.total,
                "feedback": score.feedback,
            },
        }

    return {"session_id": session_id, "status": session.status.value, "score": None}


@router.get("/{session_id}/results")
def get_results(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    scoring_engine: ScoringEngine = Depends(get_scoring_engine),
    case_index: dict = Depends(get_case_index),
):
    """Get the full debrief and results for a completed session."""
    try:
        session = session_manager.get_session_or_raise(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Session not yet completed")

    case_data = case_index.get(session.case_id, {})
    case = Case(**case_data) if case_data else None
    score = scoring_engine.score_session(session, case) if case else None

    correct_diagnoses = [
        {"icd9_code": d["icd9_code"], "description": d["description"], "is_primary": d["is_primary"]}
        for d in case_data.get("diagnoses", [])
    ] if case_data else []

    return {
        "session_id": session_id,
        "case_id": session.case_id,
        "submitted_diagnosis": session.submitted_diagnosis,
        "submitted_differentials": session.submitted_differentials,
        "correct_diagnoses": correct_diagnoses,
        "elapsed_seconds": session.elapsed_seconds,
        "resources_used": {
            "questions": session.question_count,
            "labs": session.lab_count,
            "exams": session.exam_count,
        },
        "score": {
            "primary_diagnosis": score.primary_diagnosis,
            "differential": score.differential,
            "efficiency": score.efficiency,
            "time_bonus": score.time_bonus,
            "total": score.total,
            "feedback": score.feedback,
        } if score else None,
        "action_log": [
            {
                "action_type": a.action_type.value,
                "detail": a.detail,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in session.action_log
        ],
    }