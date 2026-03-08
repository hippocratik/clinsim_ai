import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from app.data.parser import parse_discharge_summary, build_case_from_parsed

@pytest.mark.asyncio
async def test_parse_discharge_summary():
    mock_llm_response = json.dumps({
        "presenting_complaint": "Chest pain",
        "hpi": "3 hours of chest pain",
        "past_medical_history": ["HTN", "DM"],
        "medications": ["Metformin"],
        "allergies": [],
        "physical_exam": {
            "vitals": {"heart_rate": 98, "blood_pressure": "140/90", "respiratory_rate": 18, "temperature": 37.0, "spo2": 96},
            "findings": "S3 gallop"
        },
        "hospital_course": "Treated for STEMI",
        "discharge_diagnosis": "Acute MI"
    })

    with patch("app.data.parser.LLMService") as mock_llm:
        mock_llm.return_value.generate = AsyncMock(return_value=mock_llm_response)

        result = await parse_discharge_summary(
            llm_service=mock_llm.return_value,
            discharge_summary="Patient admitted with chest pain..."
        )

        assert result["presenting_complaint"] == "Chest pain"
        assert result["past_medical_history"] == ["HTN", "DM"]

def test_build_case_from_parsed():
    parsed = {
        "presenting_complaint": "Chest pain",
        "hpi": "3 hours of chest pain",
        "past_medical_history": ["HTN"],
        "medications": ["Aspirin"],
        "allergies": [],
        "physical_exam": {
            "vitals": {"heart_rate": 98, "blood_pressure": "140/90", "respiratory_rate": 18, "temperature": 37.0, "spo2": 96},
            "findings": "Normal"
        },
        "hospital_course": "Treated",
        "discharge_diagnosis": "MI"
    }

    diagnoses = [{"icd9_code": "410.11", "description": "Acute MI", "seq_num": 1}]
    labs = [{"label": "Troponin", "value": 0.5, "valueuom": "ng/mL", "flag": "abnormal"}]

    case = build_case_from_parsed(
        parsed=parsed,
        subject_id=123,
        hadm_id=456,
        diagnoses=diagnoses,
        labs=labs,
        age=55,
        gender="M"
    )

    assert case.case_id == "case_456"
    assert case.demographics.age == 55
    assert len(case.diagnoses) == 1
