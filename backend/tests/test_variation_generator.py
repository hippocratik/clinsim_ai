import pytest
import json
from unittest.mock import Mock, AsyncMock
from app.generation.variation_generator import (
    VariationGenerator,
    VARIATION_GENERATION_SYSTEM_PROMPT
)
from app.generation.models import ClinicalTemplate, VariationParameters


@pytest.fixture
def sample_template():
    return ClinicalTemplate(
        source_case_id="case_001",
        primary_diagnosis="Acute Myocardial Infarction",
        icd9_code="410.11",
        diagnosis_category="cardiac",
        cardinal_symptoms=["chest pain", "diaphoresis", "radiation to arm"],
        supporting_symptoms=["nausea", "shortness of breath"],
        critical_lab_patterns=[
            {"lab_name": "Troponin", "pattern": "elevated", "typical_range": ">0.04 ng/mL"}
        ],
        critical_exam_findings=["S3 gallop", "diaphoresis"],
        symptom_timeline="acute",
        risk_factors=["hypertension", "diabetes", "smoking"],
        age_range=(40, 80),
        valid_genders=["M", "F"],
        common_differentials=["unstable angina", "pericarditis", "aortic dissection"],
        distinguishing_features=["ST elevation", "elevated troponin", "sudden onset"]
    )


@pytest.fixture
def mock_rag_results():
    return [
        {
            "case_id": "ref_001",
            "content": "65yo M with chest pain, troponin 0.8 ng/mL, BP 140/90",
            "score": 0.95
        },
        {
            "case_id": "ref_002",
            "content": "72yo F with substernal chest pressure, troponin 1.2 ng/mL",
            "score": 0.88
        }
    ]


def test_system_prompt_contains_required_rules():
    assert "MUST have the same underlying diagnosis" in VARIATION_GENERATION_SYSTEM_PROMPT
    assert "clinically plausible" in VARIATION_GENERATION_SYSTEM_PROMPT
    assert "reference cases" in VARIATION_GENERATION_SYSTEM_PROMPT
    assert "JSON" in VARIATION_GENERATION_SYSTEM_PROMPT
    assert "DIFFERENT from the source" in VARIATION_GENERATION_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_generate_variation_returns_case_dict(sample_template, mock_rag_results):
    mock_llm_response = json.dumps({
        "case_id": "gen_001",
        "subject_id": 999,
        "hadm_id": 888,
        "demographics": {
            "age": 58,
            "gender": "M",
            "admission_type": "EMERGENCY"
        },
        "presenting_complaint": "Crushing chest pain for 2 hours",
        "hpi": "58yo male with sudden onset crushing chest pain radiating to left jaw",
        "past_medical_history": ["Hypertension", "Hyperlipidemia"],
        "medications": ["Atorvastatin", "Amlodipine"],
        "allergies": [],
        "physical_exam": {
            "vitals": {
                "heart_rate": 102,
                "blood_pressure": "158/94",
                "respiratory_rate": 24,
                "temperature": 37.0,
                "spo2": 95
            },
            "findings": "Diaphoretic, anxious, regular rhythm"
        },
        "available_labs": [
            {"lab_name": "Troponin", "value": "0.89", "unit": "ng/mL", "flag": "critical"}
        ],
        "diagnoses": [
            {"icd9_code": "410.11", "description": "Acute Myocardial Infarction", "is_primary": True}
        ],
        "discharge_summary": "Patient treated for acute STEMI",
        "difficulty": "medium",
        "specialties": ["cardiology"],
        "is_generated": True
    })

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value=mock_llm_response)

    mock_rag = Mock()
    mock_rag.search = AsyncMock(return_value=mock_rag_results)

    generator = VariationGenerator(llm_service=mock_llm, rag_service=mock_rag)
    result = await generator.generate_variation(sample_template)

    assert isinstance(result, dict)
    assert result["case_id"] == "gen_001"
    assert result["is_generated"] is True
    assert result["demographics"]["age"] == 58


@pytest.mark.asyncio
async def test_generate_variation_uses_rag_for_grounding(sample_template, mock_rag_results):
    mock_llm_response = json.dumps({
        "case_id": "gen_002",
        "subject_id": 1000,
        "hadm_id": 900,
        "demographics": {"age": 62, "gender": "F", "admission_type": "EMERGENCY"},
        "presenting_complaint": "Chest tightness",
        "hpi": "Patient reports chest discomfort",
        "past_medical_history": [],
        "medications": [],
        "allergies": [],
        "physical_exam": {
            "vitals": {"heart_rate": 90, "blood_pressure": "130/85", "respiratory_rate": 18, "temperature": 36.8, "spo2": 97},
            "findings": "Normal"
        },
        "available_labs": [],
        "diagnoses": [{"icd9_code": "410.11", "description": "AMI", "is_primary": True}],
        "discharge_summary": "Treated for MI",
        "difficulty": "easy",
        "specialties": ["cardiology"],
        "is_generated": True
    })

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value=mock_llm_response)

    mock_rag = Mock()
    mock_rag.search = AsyncMock(return_value=mock_rag_results)

    generator = VariationGenerator(llm_service=mock_llm, rag_service=mock_rag)
    await generator.generate_variation(sample_template)

    # Verify RAG was called to retrieve similar cases
    mock_rag.search.assert_called_once()
    search_query = mock_rag.search.call_args[0][0]
    assert "Acute Myocardial Infarction" in search_query or "cardiac" in search_query


@pytest.mark.asyncio
async def test_generate_variation_with_parameters(sample_template, mock_rag_results):
    mock_llm_response = json.dumps({
        "case_id": "gen_003",
        "subject_id": 1001,
        "hadm_id": 901,
        "demographics": {"age": 75, "gender": "F", "admission_type": "EMERGENCY"},
        "presenting_complaint": "Fatigue and nausea",
        "hpi": "Atypical presentation with fatigue",
        "past_medical_history": ["Diabetes", "CKD"],
        "medications": [],
        "allergies": [],
        "physical_exam": {
            "vitals": {"heart_rate": 88, "blood_pressure": "145/88", "respiratory_rate": 20, "temperature": 36.9, "spo2": 94},
            "findings": "Appears fatigued"
        },
        "available_labs": [{"lab_name": "Troponin", "value": "1.5", "unit": "ng/mL", "flag": "critical"}],
        "diagnoses": [{"icd9_code": "410.11", "description": "AMI", "is_primary": True}],
        "discharge_summary": "Atypical MI presentation",
        "difficulty": "hard",
        "specialties": ["cardiology"],
        "is_generated": True
    })

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value=mock_llm_response)

    mock_rag = Mock()
    mock_rag.search = AsyncMock(return_value=mock_rag_results)

    params = VariationParameters(
        age=75,
        gender="F",
        add_comorbidities=["Diabetes", "CKD"],
        atypical_presentation=True,
        symptom_severity="severe"
    )

    generator = VariationGenerator(llm_service=mock_llm, rag_service=mock_rag)
    result = await generator.generate_variation(sample_template, params)

    # Verify LLM was called with parameters included in prompt
    mock_llm.generate.assert_called_once()
    call_args = mock_llm.generate.call_args
    prompt = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
    assert "75" in prompt or "atypical" in prompt.lower()


@pytest.mark.asyncio
async def test_generate_batch_returns_multiple_cases(sample_template, mock_rag_results):
    def make_mock_response(idx):
        return json.dumps({
            "case_id": f"gen_batch_{idx}",
            "subject_id": 2000 + idx,
            "hadm_id": 3000 + idx,
            "demographics": {"age": 50 + idx, "gender": "M", "admission_type": "EMERGENCY"},
            "presenting_complaint": f"Chest pain variant {idx}",
            "hpi": f"History variant {idx}",
            "past_medical_history": [],
            "medications": [],
            "allergies": [],
            "physical_exam": {
                "vitals": {"heart_rate": 90, "blood_pressure": "130/80", "respiratory_rate": 18, "temperature": 37.0, "spo2": 96},
                "findings": "Normal"
            },
            "available_labs": [],
            "diagnoses": [{"icd9_code": "410.11", "description": "AMI", "is_primary": True}],
            "discharge_summary": f"Discharge {idx}",
            "difficulty": "medium",
            "specialties": ["cardiology"],
            "is_generated": True
        })

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(side_effect=[make_mock_response(i) for i in range(3)])

    mock_rag = Mock()
    mock_rag.search = AsyncMock(return_value=mock_rag_results)

    generator = VariationGenerator(llm_service=mock_llm, rag_service=mock_rag)
    results = await generator.generate_batch(sample_template, count=3)

    assert len(results) == 3
    assert all(r["is_generated"] is True for r in results)
    assert results[0]["case_id"] == "gen_batch_0"
    assert results[1]["case_id"] == "gen_batch_1"
    assert results[2]["case_id"] == "gen_batch_2"
