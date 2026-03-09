import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from app.generation.template_extractor import (
    TemplateExtractor,
    TEMPLATE_EXTRACTION_SYSTEM_PROMPT
)
from app.generation.models import ClinicalTemplate
from app.models import Case, Demographics, PhysicalExam, Vitals, LabResult, Diagnosis


@pytest.fixture
def sample_case():
    return Case(
        case_id="case_001",
        subject_id=123,
        hadm_id=456,
        demographics=Demographics(age=55, gender="M", admission_type="EMERGENCY"),
        presenting_complaint="Chest pain for 3 hours",
        hpi="Patient reports sudden onset substernal chest pain radiating to left arm",
        past_medical_history=["Hypertension", "Diabetes", "Smoking"],
        medications=["Metformin", "Lisinopril"],
        allergies=["Penicillin"],
        physical_exam=PhysicalExam(
            vitals=Vitals(heart_rate=98, blood_pressure="145/92", respiratory_rate=22, temperature=37.2, spo2=94),
            findings="S3 gallop noted, diaphoretic"
        ),
        available_labs=[
            LabResult(lab_name="Troponin", value="0.52", unit="ng/mL", flag="critical")
        ],
        diagnoses=[
            Diagnosis(icd9_code="410.11", description="Acute Myocardial Infarction", is_primary=True)
        ],
        discharge_summary="Patient treated for STEMI",
        difficulty="medium",
        specialties=["cardiology"],
        is_generated=False
    )


def test_system_prompt_contains_required_fields():
    assert "cardinal_symptoms" in TEMPLATE_EXTRACTION_SYSTEM_PROMPT
    assert "critical_lab_patterns" in TEMPLATE_EXTRACTION_SYSTEM_PROMPT
    assert "diagnosis_category" in TEMPLATE_EXTRACTION_SYSTEM_PROMPT
    assert "age_range" in TEMPLATE_EXTRACTION_SYSTEM_PROMPT
    assert "common_differentials" in TEMPLATE_EXTRACTION_SYSTEM_PROMPT
    assert "JSON" in TEMPLATE_EXTRACTION_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_extract_template_from_case(sample_case):
    mock_llm_response = json.dumps({
        "primary_diagnosis": "Acute Myocardial Infarction",
        "icd9_code": "410.11",
        "diagnosis_category": "cardiac",
        "cardinal_symptoms": ["chest pain", "diaphoresis", "radiation to arm"],
        "supporting_symptoms": ["nausea", "shortness of breath"],
        "critical_lab_patterns": [
            {"lab_name": "Troponin", "pattern": "elevated", "typical_range": ">0.04 ng/mL"}
        ],
        "critical_exam_findings": ["S3 gallop", "diaphoresis"],
        "symptom_timeline": "acute",
        "risk_factors": ["hypertension", "diabetes", "smoking"],
        "age_range": [40, 80],
        "valid_genders": ["M", "F"],
        "common_differentials": ["unstable angina", "pericarditis", "aortic dissection"],
        "distinguishing_features": ["ST elevation", "elevated troponin", "sudden onset"]
    })

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value=mock_llm_response)

    extractor = TemplateExtractor(llm_service=mock_llm)
    template = await extractor.extract_template(sample_case)

    assert isinstance(template, ClinicalTemplate)
    assert template.source_case_id == "case_001"
    assert template.primary_diagnosis == "Acute Myocardial Infarction"
    assert template.diagnosis_category == "cardiac"
    assert "chest pain" in template.cardinal_symptoms
    assert template.age_range == (40, 80)


@pytest.mark.asyncio
async def test_extract_template_calls_llm_correctly(sample_case):
    mock_llm_response = json.dumps({
        "primary_diagnosis": "Test",
        "icd9_code": "000.00",
        "diagnosis_category": "other",
        "cardinal_symptoms": [],
        "supporting_symptoms": [],
        "critical_lab_patterns": [],
        "critical_exam_findings": [],
        "symptom_timeline": "acute",
        "risk_factors": [],
        "age_range": [0, 100],
        "valid_genders": ["M", "F"],
        "common_differentials": [],
        "distinguishing_features": []
    })

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value=mock_llm_response)

    extractor = TemplateExtractor(llm_service=mock_llm)
    await extractor.extract_template(sample_case)

    # Verify LLM was called with correct prompt
    mock_llm.generate.assert_called_once()
    call_args = mock_llm.generate.call_args
    assert TEMPLATE_EXTRACTION_SYSTEM_PROMPT in call_args.kwargs.get("system_prompt", call_args.args[0] if call_args.args else "")
