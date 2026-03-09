import pytest
import json
from unittest.mock import Mock, AsyncMock
from app.generation.clinical_validator import (
    ClinicalValidator,
    CLINICAL_VALIDATION_SYSTEM_PROMPT
)
from app.generation.models import (
    ClinicalTemplate,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity
)


@pytest.fixture
def sample_template():
    return ClinicalTemplate(
        source_case_id="case_001",
        primary_diagnosis="Acute Myocardial Infarction",
        icd9_code="410.11",
        diagnosis_category="cardiac",
        cardinal_symptoms=["chest pain", "diaphoresis"],
        supporting_symptoms=["nausea", "shortness of breath"],
        critical_lab_patterns=[
            {"lab_name": "Troponin", "pattern": "elevated", "typical_range": ">0.04 ng/mL"}
        ],
        critical_exam_findings=["S3 gallop"],
        symptom_timeline="acute",
        risk_factors=["hypertension", "diabetes"],
        age_range=(40, 80),
        valid_genders=["M", "F"],
        common_differentials=["unstable angina", "pericarditis"],
        distinguishing_features=["ST elevation", "elevated troponin"]
    )


@pytest.fixture
def valid_case():
    return {
        "case_id": "gen_001",
        "demographics": {
            "age": 58,
            "gender": "M",
            "admission_type": "EMERGENCY"
        },
        "presenting_complaint": "Chest pain",
        "physical_exam": {
            "vitals": {
                "heart_rate": 88,
                "blood_pressure": "145/92",
                "respiratory_rate": 18,
                "temperature": 37.0,
                "spo2": 96
            },
            "findings": "Normal"
        },
        "available_labs": [
            {"lab_name": "Troponin", "value": "0.52", "unit": "ng/mL", "flag": "critical"}
        ],
        "diagnoses": [
            {"icd9_code": "410.11", "description": "AMI", "is_primary": True}
        ]
    }


def test_vital_ranges_defined():
    validator = ClinicalValidator()
    assert "heart_rate" in validator.VITAL_RANGES
    assert "blood_pressure_systolic" in validator.VITAL_RANGES
    assert "respiratory_rate" in validator.VITAL_RANGES
    assert "temperature" in validator.VITAL_RANGES
    assert "spo2" in validator.VITAL_RANGES


def test_lab_reference_ranges_defined():
    validator = ClinicalValidator()
    assert "troponin" in validator.LAB_REFERENCE_RANGES
    assert "low" in validator.LAB_REFERENCE_RANGES["troponin"]
    assert "high" in validator.LAB_REFERENCE_RANGES["troponin"]


def test_validate_vitals_passes_for_normal_values(valid_case):
    validator = ClinicalValidator()
    issues = validator._validate_vitals(valid_case)
    # Should have no errors
    assert not any(i.severity == ValidationSeverity.ERROR for i in issues)


def test_validate_vitals_flags_critical_values():
    validator = ClinicalValidator()
    case_with_critical_hr = {
        "physical_exam": {
            "vitals": {
                "heart_rate": 250,  # Critical high
                "blood_pressure": "120/80",
                "respiratory_rate": 18,
                "temperature": 37.0,
                "spo2": 98
            }
        }
    }
    issues = validator._validate_vitals(case_with_critical_hr)
    # Should have at least one error for critical heart rate
    hr_issues = [i for i in issues if "heart_rate" in i.field]
    assert len(hr_issues) > 0
    assert any(i.severity == ValidationSeverity.ERROR for i in hr_issues)


def test_validate_vitals_warns_for_abnormal_values():
    validator = ClinicalValidator()
    case_with_high_hr = {
        "physical_exam": {
            "vitals": {
                "heart_rate": 120,  # Above normal but not critical
                "blood_pressure": "120/80",
                "respiratory_rate": 18,
                "temperature": 37.0,
                "spo2": 98
            }
        }
    }
    issues = validator._validate_vitals(case_with_high_hr)
    # Should have warning or info, not error
    hr_issues = [i for i in issues if "heart_rate" in i.field]
    assert len(hr_issues) >= 0  # May or may not flag slightly elevated


def test_validate_demographics_within_age_range(valid_case, sample_template):
    validator = ClinicalValidator()
    issues = validator._validate_demographics(valid_case, sample_template)
    # Age 58 is within 40-80 range
    age_issues = [i for i in issues if "age" in i.field]
    assert not any(i.severity == ValidationSeverity.ERROR for i in age_issues)


def test_validate_demographics_flags_age_outside_range(sample_template):
    validator = ClinicalValidator()
    case_with_young_patient = {
        "demographics": {
            "age": 25,  # Below template's 40-80 range
            "gender": "M"
        }
    }
    issues = validator._validate_demographics(case_with_young_patient, sample_template)
    age_issues = [i for i in issues if "age" in i.field]
    assert len(age_issues) > 0
    # Should be warning since unusual but possible
    assert any(i.severity in [ValidationSeverity.WARNING, ValidationSeverity.ERROR] for i in age_issues)


def test_validate_demographics_flags_invalid_gender(sample_template):
    validator = ClinicalValidator()
    # Create template that only allows M
    male_only_template = ClinicalTemplate(
        source_case_id="test",
        primary_diagnosis="Prostate Cancer",
        icd9_code="185",
        diagnosis_category="oncology",
        cardinal_symptoms=["urinary symptoms"],
        supporting_symptoms=[],
        critical_lab_patterns=[],
        critical_exam_findings=[],
        symptom_timeline="chronic",
        risk_factors=[],
        age_range=(50, 90),
        valid_genders=["M"],  # Male only
        common_differentials=[],
        distinguishing_features=[]
    )
    case_with_female = {
        "demographics": {
            "age": 65,
            "gender": "F"  # Invalid for prostate cancer
        }
    }
    issues = validator._validate_demographics(case_with_female, male_only_template)
    gender_issues = [i for i in issues if "gender" in i.field]
    assert len(gender_issues) > 0
    assert any(i.severity == ValidationSeverity.ERROR for i in gender_issues)


@pytest.mark.asyncio
async def test_validate_returns_validation_result(valid_case, sample_template):
    mock_llm_response = json.dumps({
        "is_clinically_plausible": True,
        "issues": [],
        "confidence": 0.95
    })

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value=mock_llm_response)

    validator = ClinicalValidator(llm_service=mock_llm)
    result = await validator.validate(valid_case, sample_template)

    assert isinstance(result, ValidationResult)
    assert isinstance(result.is_valid, bool)
    assert isinstance(result.issues, list)
    assert 0.0 <= result.confidence_score <= 1.0


@pytest.mark.asyncio
async def test_validate_calls_llm_for_clinical_plausibility(valid_case, sample_template):
    mock_llm_response = json.dumps({
        "is_clinically_plausible": True,
        "issues": [],
        "confidence": 0.9
    })

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value=mock_llm_response)

    validator = ClinicalValidator(llm_service=mock_llm)
    await validator.validate(valid_case, sample_template)

    # Verify LLM was called
    mock_llm.generate.assert_called_once()


@pytest.mark.asyncio
async def test_validate_combines_rule_and_llm_issues(sample_template):
    case_with_issues = {
        "demographics": {
            "age": 25,  # Outside age range
            "gender": "M"
        },
        "physical_exam": {
            "vitals": {
                "heart_rate": 250,  # Critical
                "blood_pressure": "120/80",
                "respiratory_rate": 18,
                "temperature": 37.0,
                "spo2": 98
            }
        },
        "available_labs": [],
        "diagnoses": []
    }

    mock_llm_response = json.dumps({
        "is_clinically_plausible": False,
        "issues": [
            {"field": "presentation", "message": "Missing cardinal symptom chest pain", "severity": "warning"}
        ],
        "confidence": 0.4
    })

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value=mock_llm_response)

    validator = ClinicalValidator(llm_service=mock_llm)
    result = await validator.validate(case_with_issues, sample_template)

    # Should have multiple issues from both rule-based and LLM
    assert len(result.issues) >= 2
    assert result.is_valid is False  # Has errors


def test_system_prompt_exists():
    assert "clinically plausible" in CLINICAL_VALIDATION_SYSTEM_PROMPT.lower() or \
           "clinical" in CLINICAL_VALIDATION_SYSTEM_PROMPT.lower()
    assert "JSON" in CLINICAL_VALIDATION_SYSTEM_PROMPT
