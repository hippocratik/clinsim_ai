import pytest
from app.rag.chunker import chunk_case
from app.models import Case, Demographics, PhysicalExam, Vitals, LabResult, Diagnosis

@pytest.fixture
def sample_case():
    return Case(
        case_id="case_001",
        subject_id=123,
        hadm_id=456,
        demographics=Demographics(age=55, gender="M", admission_type="EMERGENCY"),
        presenting_complaint="Chest pain for 3 hours",
        hpi="Patient reports sudden onset substernal chest pain",
        past_medical_history=["Hypertension", "Diabetes"],
        medications=["Metformin", "Lisinopril"],
        allergies=["Penicillin"],
        physical_exam=PhysicalExam(
            vitals=Vitals(heart_rate=98, blood_pressure="145/92", respiratory_rate=22, temperature=37.2, spo2=94),
            findings="S3 gallop noted"
        ),
        available_labs=[
            LabResult(lab_name="Troponin", value="0.52", unit="ng/mL", flag="critical")
        ],
        diagnoses=[
            Diagnosis(icd9_code="410.11", description="Acute MI", is_primary=True)
        ],
        discharge_summary="Patient treated for STEMI",
        difficulty="medium",
        specialties=["cardiology"],
        is_generated=False
    )

def test_chunk_case_creates_all_chunk_types(sample_case):
    chunks = chunk_case(sample_case)

    chunk_types = [c.chunk_type for c in chunks]

    assert "presenting_complaint" in chunk_types
    assert "pmh" in chunk_types
    assert "physical_exam" in chunk_types
    assert "labs" in chunk_types
    assert "medications" in chunk_types
    assert "diagnosis" in chunk_types

def test_chunk_case_includes_metadata(sample_case):
    chunks = chunk_case(sample_case)

    for chunk in chunks:
        assert chunk.case_id == "case_001"
        assert chunk.metadata["subject_id"] == 123
        assert chunk.metadata["hadm_id"] == 456

def test_chunk_content_is_meaningful(sample_case):
    chunks = chunk_case(sample_case)

    presenting_chunk = next(c for c in chunks if c.chunk_type == "presenting_complaint")
    assert "Chest pain" in presenting_chunk.content

    pmh_chunk = next(c for c in chunks if c.chunk_type == "pmh")
    assert "Hypertension" in pmh_chunk.content
