import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ActionType(str, Enum):
    CHAT = "chat"
    LAB_ORDER = "lab_order"
    EXAM = "exam"
    DIAGNOSIS = "diagnosis"


@dataclass
class ChatMessage:
    role: str  # "trainee" | "patient"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LabOrder:
    lab_name: str
    result: Optional[str] = None
    ordered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExamAction:
    system: str  # e.g. "cardiovascular", "respiratory"
    findings: str
    performed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RecordedAction:
    action_type: ActionType
    detail: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Session:
    session_id: str
    case_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Conversation
    chat_history: list[ChatMessage] = field(default_factory=list)

    # Resources used
    labs_ordered: list[LabOrder] = field(default_factory=list)
    exams_performed: list[ExamAction] = field(default_factory=list)

    # Limits
    max_questions: int = 20
    max_labs: int = 10
    max_exams: int = 5

    # Diagnosis submission
    submitted_diagnosis: Optional[str] = None
    submitted_differentials: list[str] = field(default_factory=list)

    # Action log (for scoring/audit)
    action_log: list[RecordedAction] = field(default_factory=list)

    @property
    def question_count(self) -> int:
        return sum(1 for m in self.chat_history if m.role == "trainee")

    @property
    def lab_count(self) -> int:
        return len(self.labs_ordered)

    @property
    def exam_count(self) -> int:
        return len(self.exams_performed)

    @property
    def elapsed_seconds(self) -> float:
        end = self.completed_at or datetime.utcnow()
        return (end - self.started_at).total_seconds()

    def can_ask_question(self) -> bool:
        return self.status == SessionStatus.ACTIVE and self.question_count < self.max_questions

    def can_order_lab(self) -> bool:
        return self.status == SessionStatus.ACTIVE and self.lab_count < self.max_labs

    def can_perform_exam(self) -> bool:
        return self.status == SessionStatus.ACTIVE and self.exam_count < self.max_exams


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self, case_id: str) -> Session:
        """Create a new simulation session."""
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id, case_id=case_id)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)

    def get_session_or_raise(self, session_id: str) -> Session:
        """Retrieve session or raise KeyError."""
        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"Session '{session_id}' not found")
        return session

    def list_sessions(self, case_id: str = None) -> list[Session]:
        """List all sessions, optionally filtered by case_id."""
        sessions = list(self._sessions.values())
        if case_id:
            sessions = [s for s in sessions if s.case_id == case_id]
        return sessions

    def add_chat_message(self, session_id: str, role: str, content: str) -> ChatMessage:
        """Append a chat message to the session."""
        session = self.get_session_or_raise(session_id)
        msg = ChatMessage(role=role, content=content)
        session.chat_history.append(msg)
        session.action_log.append(RecordedAction(
            action_type=ActionType.CHAT,
            detail=f"{role}: {content[:80]}"
        ))
        return msg

    def record_lab_order(self, session_id: str, lab_name: str, result: str = None) -> LabOrder:
        """Record a lab order in the session."""
        session = self.get_session_or_raise(session_id)
        if not session.can_order_lab():
            raise ValueError(f"Lab limit ({session.max_labs}) reached or session not active")
        lab = LabOrder(lab_name=lab_name, result=result)
        session.labs_ordered.append(lab)
        session.action_log.append(RecordedAction(
            action_type=ActionType.LAB_ORDER,
            detail=f"Ordered: {lab_name}"
        ))
        return lab

    def record_exam(self, session_id: str, system: str, findings: str) -> ExamAction:
        """Record a physical exam action."""
        session = self.get_session_or_raise(session_id)
        if not session.can_perform_exam():
            raise ValueError(f"Exam limit ({session.max_exams}) reached or session not active")
        exam = ExamAction(system=system, findings=findings)
        session.exams_performed.append(exam)
        session.action_log.append(RecordedAction(
            action_type=ActionType.EXAM,
            detail=f"Exam: {system} — {findings[:80]}"
        ))
        return exam

    def submit_diagnosis(
        self,
        session_id: str,
        primary_diagnosis: str,
        differentials: list[str] = None
    ) -> Session:
        """Submit a diagnosis and mark session as completed."""
        session = self.get_session_or_raise(session_id)
        if session.status != SessionStatus.ACTIVE:
            raise ValueError("Cannot submit diagnosis: session is not active")
        session.submitted_diagnosis = primary_diagnosis
        session.submitted_differentials = differentials or []
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        session.action_log.append(RecordedAction(
            action_type=ActionType.DIAGNOSIS,
            detail=f"Primary: {primary_diagnosis}"
        ))
        return session

    def abandon_session(self, session_id: str) -> Session:
        """Mark a session as abandoned."""
        session = self.get_session_or_raise(session_id)
        session.status = SessionStatus.ABANDONED
        session.completed_at = datetime.utcnow()
        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from memory."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False