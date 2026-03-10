import pytest
from app.core.session_manager import SessionManager, SessionStatus, ActionType


@pytest.fixture
def manager():
    return SessionManager()


def test_create_session(manager):
    session = manager.create_session("case_001")
    assert session.case_id == "case_001"
    assert session.status == SessionStatus.ACTIVE
    assert session.session_id is not None


def test_get_session(manager):
    session = manager.create_session("case_001")
    fetched = manager.get_session(session.session_id)
    assert fetched is session


def test_get_missing_session_returns_none(manager):
    assert manager.get_session("nonexistent") is None


def test_get_session_or_raise(manager):
    with pytest.raises(KeyError):
        manager.get_session_or_raise("nonexistent")


def test_add_chat_message(manager):
    session = manager.create_session("case_001")
    msg = manager.add_chat_message(session.session_id, "trainee", "How are you feeling?")
    assert msg.role == "trainee"
    assert msg.content == "How are you feeling?"
    assert session.question_count == 1


def test_question_limit_enforced(manager):
    session = manager.create_session("case_001")
    session.max_questions = 2
    manager.add_chat_message(session.session_id, "trainee", "Q1")
    manager.add_chat_message(session.session_id, "patient", "A1")
    manager.add_chat_message(session.session_id, "trainee", "Q2")
    assert not session.can_ask_question()


def test_record_lab_order(manager):
    session = manager.create_session("case_001")
    lab = manager.record_lab_order(session.session_id, "Troponin", "0.52 ng/mL (critical)")
    assert lab.lab_name == "Troponin"
    assert session.lab_count == 1


def test_lab_limit_enforced(manager):
    session = manager.create_session("case_001")
    session.max_labs = 1
    manager.record_lab_order(session.session_id, "Troponin")
    with pytest.raises(ValueError, match="Lab limit"):
        manager.record_lab_order(session.session_id, "BMP")


def test_record_exam(manager):
    session = manager.create_session("case_001")
    exam = manager.record_exam(session.session_id, "cardiovascular", "S3 gallop")
    assert exam.system == "cardiovascular"
    assert session.exam_count == 1


def test_exam_limit_enforced(manager):
    session = manager.create_session("case_001")
    session.max_exams = 1
    manager.record_exam(session.session_id, "cardiovascular", "Normal")
    with pytest.raises(ValueError, match="Exam limit"):
        manager.record_exam(session.session_id, "respiratory", "Clear")


def test_submit_diagnosis(manager):
    session = manager.create_session("case_001")
    updated = manager.submit_diagnosis(session.session_id, "410.11", ["428.0", "414.01"])
    assert updated.status == SessionStatus.COMPLETED
    assert updated.submitted_diagnosis == "410.11"
    assert len(updated.submitted_differentials) == 2
    assert updated.completed_at is not None


def test_cannot_submit_diagnosis_twice(manager):
    session = manager.create_session("case_001")
    manager.submit_diagnosis(session.session_id, "410.11")
    with pytest.raises(ValueError, match="not active"):
        manager.submit_diagnosis(session.session_id, "428.0")


def test_action_log_populated(manager):
    session = manager.create_session("case_001")
    manager.add_chat_message(session.session_id, "trainee", "Hello")
    manager.record_lab_order(session.session_id, "CBC")
    manager.record_exam(session.session_id, "abdominal", "Soft")
    manager.submit_diagnosis(session.session_id, "540.9")

    types = [a.action_type for a in session.action_log]
    assert ActionType.CHAT in types
    assert ActionType.LAB_ORDER in types
    assert ActionType.EXAM in types
    assert ActionType.DIAGNOSIS in types


def test_delete_session(manager):
    session = manager.create_session("case_001")
    sid = session.session_id
    assert manager.delete_session(sid) is True
    assert manager.get_session(sid) is None


def test_elapsed_seconds(manager):
    session = manager.create_session("case_001")
    assert session.elapsed_seconds >= 0