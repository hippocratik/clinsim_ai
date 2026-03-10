import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.generation.models import ClinicalTemplate

MOCK_CASE = {
    "case_id": "case_001",
    "subject_id": 1001,
    "hadm_id": 100001,
    "demographics": {"age": 65, "gender": "M", "admission_type": "EMERGENCY"},
    "presenting_complaint": "Chest pain and shortness of breath",
    "hpi": "65-year-old male presenting with acute chest pain.",
    "past_medical_history": ["Hypertension", "Diabetes"],
    "medications": ["Metformin", "Lisinopril"],
    "allergies": ["Penicillin"],
    "physical_exam": {
        "vitals": {
            "heart_rate": 95,
            "blood_pressure": "150/90",
            "respiratory_rate": 18,
            "temperature": 98.6,
            "spo2": 97,
        },
        "findings": "Mild chest tenderness on palpation.",
    },
    "available_labs": [
        {"lab_name": "Troponin", "value": "2.5", "unit": "ng/mL", "flag": "critical"}
    ],
    "diagnoses": [
        {"icd9_code": "410.11", "description": "STEMI", "is_primary": True}
    ],
    "discharge_summary": "Patient admitted with STEMI.",
    "difficulty": "hard",
    "specialties": ["cardiology"],
    "is_generated": False,
}

MOCK_TEMPLATE = ClinicalTemplate(
    source_case_id="case_001",
    primary_diagnosis="STEMI",
    icd9_code="410.11",
    diagnosis_category="cardiac",
    cardinal_symptoms=["chest pain"],
    supporting_symptoms=["shortness of breath"],
    critical_lab_patterns=[{"lab_name": "Troponin", "pattern": "elevated", "typical_range": ">0.04"}],
    critical_exam_findings=["chest tenderness"],
    symptom_timeline="hyperacute",
    risk_factors=["hypertension", "diabetes"],
    age_range=(40, 80),
    valid_genders=["M", "F"],
    common_differentials=["unstable angina", "aortic dissection"],
    distinguishing_features=["ST elevation on ECG"],
)

MOCK_GENERATED_CASE = {
    "case_id": "generated_case_abc123",
    "subject_id": 9999,
    "hadm_id": 999999,
    "demographics": {"age": 58, "gender": "F", "admission_type": "EMERGENCY"},
    "presenting_complaint": "Sudden onset chest pain",
    "hpi": "58-year-old female with acute chest pain radiating to left arm.",
    "past_medical_history": ["Hyperlipidaemia"],
    "medications": ["Atorvastatin"],
    "allergies": [],
    "physical_exam": {
        "vitals": {
            "heart_rate": 102,
            "blood_pressure": "160/95",
            "respiratory_rate": 20,
            "temperature": 98.4,
            "spo2": 96,
        },
        "findings": "Diaphoresis noted. Chest pain reproducible.",
    },
    "available_labs": [
        {"lab_name": "Troponin", "value": "3.1", "unit": "ng/mL", "flag": "critical"}
    ],
    "diagnoses": [
        {"icd9_code": "410.11", "description": "STEMI", "is_primary": True}
    ],
    "discharge_summary": "Patient admitted with STEMI, treated with PCI.",
    "difficulty": "hard",
    "specialties": ["cardiology"],
    "is_generated": True,
}


@pytest.fixture
def mock_llm():
    """Mock LLM service that returns valid JSON for generation."""
    import json
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=json.dumps(MOCK_GENERATED_CASE))
    return mock


@pytest.fixture
def mock_rag():
    """Mock RAG service that returns empty retrieval results."""
    mock = MagicMock()
    mock.retrieve_for_generation = MagicMock(return_value=[])
    mock.retrieve = MagicMock(return_value=[])
    return mock


@pytest.fixture
def mock_validator():
    """Mock ClinicalValidator that always passes."""
    from app.generation.models import ValidationResult
    mock = MagicMock()
    mock.validate = AsyncMock(return_value=MagicMock(is_valid=True))
    return mock


@pytest.fixture
def mock_extractor():
    """Mock TemplateExtractor that returns a fixed template."""
    mock = MagicMock()
    mock.extract_template = AsyncMock(return_value=MOCK_TEMPLATE)
    return mock


@pytest.fixture
def mock_generator():
    """Mock VariationGenerator that returns the mock generated case."""
    mock = MagicMock()
    mock.generate_variation = AsyncMock(return_value=MOCK_GENERATED_CASE)
    return mock


@pytest.fixture
async def client():
    """Async test client with mocked app state."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Seed app state
        app.state.case_index = {"case_001": MOCK_CASE}
        app.state.cases = [MOCK_CASE]
        app.state.generation_jobs = {}
        yield ac


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_returns_job_id(client):
    """POST /api/generate should return a job_id with pending status."""
    with patch("app.generation.template_extractor.TemplateExtractor.extract_template",
               new_callable=AsyncMock, return_value=MOCK_TEMPLATE), \
         patch("app.generation.variation_generator.VariationGenerator.generate_variation",
               new_callable=AsyncMock, return_value=MOCK_GENERATED_CASE), \
         patch("app.generation.clinical_validator.ClinicalValidator.validate",
               new_callable=AsyncMock, return_value=MagicMock(is_valid=True)):

        response = await client.post("/api/generate", json={
            "source_case_id": "case_001",
            "count": 1,
        })

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_generate_unknown_case_fails(client):
    """POST /api/generate with unknown source_case_id should fail with completed/failed status."""
    response = await client.post("/api/generate", json={
        "source_case_id": "nonexistent_case",
        "count": 1,
    })
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    # Give background task time to run
    await asyncio.sleep(0.2)

    status = await client.get(f"/api/generate/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "failed"
    assert "not found" in status.json()["error"].lower()


@pytest.mark.asyncio
async def test_generate_count_upper_bound(client):
    """POST /api/generate with count > 10 should be rejected."""
    response = await client.post("/api/generate", json={
        "source_case_id": "case_001",
        "count": 99,
    })
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_generate_count_lower_bound(client):
    """POST /api/generate with count < 1 should be rejected."""
    response = await client.post("/api/generate", json={
        "source_case_id": "case_001",
        "count": 0,
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_generation_status_not_found(client):
    """GET /api/generate/{job_id} with unknown job_id should return 404."""
    response = await client.get("/api/generate/nonexistent-job-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_case_creates_accessible_case(client):
    """Generated cases should be accessible via GET /api/cases/{case_id} after completion."""
    with patch("app.generation.template_extractor.TemplateExtractor.extract_template",
               new_callable=AsyncMock, return_value=MOCK_TEMPLATE), \
         patch("app.generation.variation_generator.VariationGenerator.generate_variation",
               new_callable=AsyncMock, return_value=MOCK_GENERATED_CASE), \
         patch("app.generation.clinical_validator.ClinicalValidator.validate",
               new_callable=AsyncMock, return_value=MagicMock(is_valid=True)):

        # POST /api/generate
        response = await client.post("/api/generate", json={
            "source_case_id": "case_001",
            "count": 1,
        })
        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Give background task time to complete
        await asyncio.sleep(0.5)

        # Poll status
        status_response = await client.get(f"/api/generate/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "completed"
        assert len(status_data["generated_case_ids"]) > 0

        # Verify each generated case is accessible
        for case_id in status_data["generated_case_ids"]:
            case_response = await client.get(f"/api/cases/{case_id}")
            assert case_response.status_code == 200  # Would fail before fix #4


@pytest.mark.asyncio
async def test_generate_invalid_case_not_persisted(client):
    """Cases that fail validation should not be added to case index."""
    with patch("app.generation.template_extractor.TemplateExtractor.extract_template",
               new_callable=AsyncMock, return_value=MOCK_TEMPLATE), \
         patch("app.generation.variation_generator.VariationGenerator.generate_variation",
               new_callable=AsyncMock, return_value=MOCK_GENERATED_CASE), \
         patch("app.generation.clinical_validator.ClinicalValidator.validate",
               new_callable=AsyncMock, return_value=MagicMock(is_valid=False)):

        response = await client.post("/api/generate", json={
            "source_case_id": "case_001",
            "count": 1,
        })
        job_id = response.json()["job_id"]

        await asyncio.sleep(0.5)

        status_response = await client.get(f"/api/generate/{job_id}")
        status_data = status_response.json()
        assert status_data["status"] == "completed"
        assert len(status_data["generated_case_ids"]) == 0