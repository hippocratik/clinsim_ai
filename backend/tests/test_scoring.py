import pytest
from app.core.scoring import ScoringEngine
from app.core.session_manager import SessionManager, SessionStatus
from app.models import (
    Case, Demographics, PhysicalExam, Vitals, LabResult, Diagnosis
)


def make_case(primary_icd9="410.11", additional_icd9=None):
    diagnoses = [Diagnosis(icd9_code=primary_icd9, description="Primary Dx", is_primary=True)]
    if additional_icd9:
        for code in additional_icd9:
            diagnoses.append(Diagnosis(icd9_code=code, description="Secondary Dx", is_primary=False))

    return Case(
        case_id="case_001",
        subject_id=1,
        hadm_id=2,
        demographics=Demographics(age=55, gender="M", admission_type="EMERGENCY"),
        presenting_complaint="Chest pain",
        hpi="3 hours of chest pain",
        past_medical_history=["HTN"],
        medications=["Aspirin"],
        allergies=[],
        physical_exam=PhysicalExam(vitals=Vitals(heart_rate=98), findings="Normal"),
        available_labs=[LabResult(lab_name="Troponin", value="0.52", unit="ng/mL", flag="critical")],
        diagnoses=diagnoses,
        discharge_summary="Admitted for STEMI",
        difficulty="medium",
        specialties=["cardiology"],
    )


def make_session_with_diagnosis(primary, differentials=None, questions=5, labs=2, exams=1):
    mgr = SessionManager()
    session = mgr.create_session("case_001")
    session.max_questions = 20
    for i in range(questions):
        mgr.add_chat_message(session.session_id, "trainee", f"Q{i}")
        mgr.add_chat_message(session.session_id, "patient", f"A{i}")
    for i in range(labs):
        mgr.record_lab_order(session.session_id, f"Lab{i}")
    for i in range(exams):
        mgr.record_exam(session.session_id, f"system{i}", "Normal")
    mgr.submit_diagnosis(session.session_id, primary, differentials or [])
    return session


@pytest.fixture
def engine():
    return ScoringEngine()


def test_correct_primary_diagnosis_scores_full(engine):
    case = make_case("410.11")
    session = make_session_with_diagnosis("410.11")
    score = engine.score_session(session, case)
    assert score.primary_diagnosis == 40


def test_wrong_primary_diagnosis_scores_zero(engine):
    case = make_case("410.11")
    session = make_session_with_diagnosis("999.99")
    score = engine.score_session(session, case)
    assert score.primary_diagnosis == 0


def test_partial_icd9_category_match_scores_partial(engine):
    case = make_case("410.11")
    session = make_session_with_diagnosis("410.99")  # same 3-digit category
    score = engine.score_session(session, case)
    assert score.primary_diagnosis == 20  # 50% of 40


def test_correct_differential_scores_points(engine):
    case = make_case("410.11", additional_icd9=["428.0"])
    session = make_session_with_diagnosis("410.11", differentials=["428.0"])
    score = engine.score_session(session, case)
    assert score.differential > 0


def test_efficiency_penalises_excess_resources(engine):
    case = make_case()
    # Use many questions and labs
    session = make_session_with_diagnosis("410.11", questions=15, labs=8, exams=4)
    score = engine.score_session(session, case)
    # Should be less than max efficiency
    assert score.efficiency < engine.EFFICIENCY_MAX


def test_ideal_resource_use_scores_full_efficiency(engine):
    case = make_case()
    session = make_session_with_diagnosis(
        "410.11",
        questions=engine.IDEAL_QUESTIONS,
        labs=engine.IDEAL_LABS,
        exams=engine.IDEAL_EXAMS,
    )
    score = engine.score_session(session, case)
    assert score.efficiency == engine.EFFICIENCY_MAX


def test_fast_session_gets_time_bonus(engine):
    case = make_case()
    session = make_session_with_diagnosis("410.11")
    # Manually adjust started_at to simulate fast completion
    from datetime import timedelta
    session.started_at = session.completed_at - timedelta(seconds=200)
    score = engine.score_session(session, case)
    assert score.time_bonus == engine.TIME_MAX


def test_slow_session_gets_no_time_bonus(engine):
    case = make_case()
    session = make_session_with_diagnosis("410.11")
    from datetime import timedelta
    session.started_at = session.completed_at - timedelta(seconds=1000)
    score = engine.score_session(session, case)
    assert score.time_bonus == 0


def test_total_score_is_sum_of_components(engine):
    case = make_case()
    session = make_session_with_diagnosis("410.11")
    score = engine.score_session(session, case)
    assert score.total == (
        score.primary_diagnosis + score.differential + score.efficiency + score.time_bonus
    )


def test_feedback_is_populated(engine):
    case = make_case()
    session = make_session_with_diagnosis("410.11")
    score = engine.score_session(session, case)
    assert len(score.feedback) > 0