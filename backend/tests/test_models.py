import pytest
from app.models import Case, CaseChunk, Demographics, PhysicalExam, Vitals, LabResult, Diagnosis

def test_case_model_validates():
    case = Case(
        case_id="case_001",
        subject_id=12345,
        hadm_id=67890,
        demographics=Demographics(age=55, gender="M", admission_type="EMERGENCY"),
        presenting_complaint="Chest pain for 3 hours",
        hpi="Patient reports sudden onset chest pain while watching TV",
        past_medical_history=["Hypertension", "Diabetes"],
        medications=["Metformin", "Lisinopril"],
        allergies=["Penicillin"],
        physical_exam=PhysicalExam(
            vitals=Vitals(heart_rate=98, blood_pressure="145/92", respiratory_rate=22, temperature=37.2, spo2=94),
            findings="S3 gallop noted, no murmurs"
        ),
        available_labs=[
            LabResult(lab_name="Troponin", value="0.52", unit="ng/mL", flag="critical")
        ],
        diagnoses=[
            Diagnosis(icd9_code="410.11", description="Acute MI, STEMI", is_primary=True)
        ],
        discharge_summary="Patient admitted for STEMI...",
        difficulty="medium",
        specialties=["cardiology"],
        is_generated=False
    )
    assert case.case_id == "case_001"
    assert case.demographics.age == 55

def test_case_chunk_model():
    chunk = CaseChunk(
        chunk_id="case_001_presenting",
        case_id="case_001",
        chunk_type="presenting_complaint",
        content="Chief complaint: Chest pain",
        metadata={"subject_id": 12345, "hadm_id": 67890, "icd9_codes": ["410.11"]}
    )
    assert chunk.chunk_type == "presenting_complaint"
