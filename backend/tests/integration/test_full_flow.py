"""
Integration tests for the full simulation flow.
These tests use TestClient and mock FAISS/LLM to avoid external dependencies.
Run with: pytest backend/tests/integration/ -v -m integration
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

# Minimal case fixture
SAMPLE_CASE = {
    "case_id": "case_001",
    "subject_id": 12345,
    "hadm_id": 67890,
    "demographics": {"age": 55, "gender": "M", "admission_type": "EMERGENCY"},
    "presenting_complaint": "Chest pain for 3 hours",
    "hpi": "Patient reports sudden onset chest pain while watching TV",
    "past_medical_history": ["Hypertension"],
    "medications": ["Aspirin"],
    "allergies": [],
    "physical_exam": {
        "vitals": {"heart_rate": 98, "blood_pressure": "145/92", "respiratory_rate": 22, "temperature": 37.2, "spo2": 94},
        "findings": "S3 gallop noted"
    },
    "available_labs": [
        {"lab_name": "Troponin", "value": "0.52", "unit": "ng/mL", "flag": "critical"}
    ],
    "diagnoses": [
        {"icd9_code": "410.11", "description": "Acute MI, STEMI", "is_primary": True}
    ],
    "discharge_summary": "Patient admitted for STEMI.",
    "difficulty": "medium",
    "specialties": ["cardiology"],
    "is_generated": False,
}


@pytest.fixture
def test_client():
    """Create a test FastAPI client with mocked services."""
    import numpy as np
    from app.core.session_manager import SessionManager
    from app.core.scoring import ScoringEngine
    from app.main import create_app

    mock_faiss = Mock()
    mock_faiss.search = Mock(return_value=(np.array([[0.1, 0.2]]), np.array([[0, 0]])))

    mock_chunks = [
        {"chunk_id": "c1", "case_id": "case_001", "chunk_type": "presenting_complaint",
         "content": "Chest pain for 3 hours", "metadata": {}}
    ]

    with patch("app.core.rag.SentenceTransformer") as mock_st:
        mock_st.return_value.encode = Mock(return_value=np.array([[0.1] * 384]))

        from app.core.rag import RAGService
        rag = RAGService(mock_faiss, mock_chunks, "all-MiniLM-L6-v2")

    mock_llm = Mock()
    mock_llm.stream = AsyncMock(return_value=iter(["I've been having chest pain."]))

    app = create_app()

    # Override lifespan state directly
    app.state.cases = [SAMPLE_CASE]
    app.state.case_index = {"case_001": SAMPLE_CASE}
    app.state.rag_service = rag
    app.state.session_manager = SessionManager()
    app.state.scoring_engine = ScoringEngine()
    app.state.llm_service = mock_llm

    with TestClient(app) as client:
        yield client


@pytest.mark.integration
def test_health_check(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["services"]["cases_loaded"] == 1


@pytest.mark.integration
def test_list_cases(test_client):
    response = test_client.get("/api/cases")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 1
    assert cases[0]["case_id"] == "case_001"


@pytest.mark.integration
def test_get_case(test_client):
    response = test_client.get("/api/cases/case_001")
    assert response.status_code == 200
    assert response.json()["case_id"] == "case_001"


@pytest.mark.integration
def test_get_missing_case(test_client):
    response = test_client.get("/api/cases/nonexistent")
    assert response.status_code == 404


@pytest.mark.integration
def test_create_session(test_client):
    response = test_client.post("/api/sessions", json={"case_id": "case_001"})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "active"


@pytest.mark.integration
def test_create_session_invalid_case(test_client):
    response = test_client.post("/api/sessions", json={"case_id": "bad_case"})
    assert response.status_code == 404


@pytest.mark.integration
def test_get_session_state(test_client):
    create_resp = test_client.post("/api/sessions", json={"case_id": "case_001"})
    sid = create_resp.json()["session_id"]

    response = test_client.get(f"/api/sessions/{sid}")
    assert response.status_code == 200
    data = response.json()
    assert data["question_count"] == 0
    assert data["lab_count"] == 0


@pytest.mark.integration
def test_order_lab(test_client):
    create_resp = test_client.post("/api/sessions", json={"case_id": "case_001"})
    sid = create_resp.json()["session_id"]

    response = test_client.post(f"/api/sessions/{sid}/labs", json={"lab_name": "Troponin"})
    assert response.status_code == 200
    data = response.json()
    assert data["lab_name"] == "Troponin"
    assert "critical" in data["result"]  # matches SAMPLE_CASE


@pytest.mark.integration
def test_perform_exam(test_client):
    create_resp = test_client.post("/api/sessions", json={"case_id": "case_001"})
    sid = create_resp.json()["session_id"]

    response = test_client.post(f"/api/sessions/{sid}/exam", json={"system": "cardiovascular"})
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == "cardiovascular"
    assert "findings" in data


@pytest.mark.integration
def test_submit_diagnosis_and_score(test_client):
    create_resp = test_client.post("/api/sessions", json={"case_id": "case_001"})
    sid = create_resp.json()["session_id"]

    response = test_client.post(f"/api/sessions/{sid}/diagnose", json={
        "primary_diagnosis": "410.11",
        "differentials": ["428.0"]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["score"]["primary_diagnosis"] == 40
    assert data["score"]["total"] > 0


@pytest.mark.integration
def test_get_results_after_diagnosis(test_client):
    create_resp = test_client.post("/api/sessions", json={"case_id": "case_001"})
    sid = create_resp.json()["session_id"]

    test_client.post(f"/api/sessions/{sid}/diagnose", json={
        "primary_diagnosis": "410.11",
        "differentials": []
    })

    response = test_client.get(f"/api/sessions/{sid}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["submitted_diagnosis"] == "410.11"
    assert "correct_diagnoses" in data
    assert len(data["correct_diagnoses"]) > 0


@pytest.mark.integration
def test_results_not_available_for_active_session(test_client):
    create_resp = test_client.post("/api/sessions", json={"case_id": "case_001"})
    sid = create_resp.json()["session_id"]

    response = test_client.get(f"/api/sessions/{sid}/results")
    assert response.status_code == 400


@pytest.mark.integration
def test_diagnoses_search(test_client):
    response = test_client.get("/api/diagnoses/search?q=chest")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    # "chest pain" should appear
    codes = [r["code"] for r in results]
    assert "786.50" in codes


@pytest.mark.integration
def test_diagnoses_search_by_icd9_code(test_client):
    response = test_client.get("/api/diagnoses/search?q=410")
    assert response.status_code == 200
    results = response.json()
    assert any("410" in r["code"] for r in results)


@pytest.mark.integration
def test_resource_limits_enforced(test_client):
    create_resp = test_client.post("/api/sessions", json={"case_id": "case_001"})
    sid = create_resp.json()["session_id"]

    # Override lab limit
    sm = None
    # Hit the lab limit (max=10)
    for i in range(10):
        test_client.post(f"/api/sessions/{sid}/labs", json={"lab_name": f"Lab{i}"})

    response = test_client.post(f"/api/sessions/{sid}/labs", json={"lab_name": "Extra"})
    assert response.status_code == 400