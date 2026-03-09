import pytest
from app.generation.models import (
    ClinicalTemplate,
    VariationParameters,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity
)


def test_clinical_template_creates():
    template = ClinicalTemplate(
        source_case_id="case_001",
        primary_diagnosis="Acute Myocardial Infarction",
        icd9_code="410.11",
        diagnosis_category="cardiac",
        cardinal_symptoms=["chest pain", "diaphoresis"],
        supporting_symptoms=["nausea", "shortness of breath"],
        critical_lab_patterns=[
            {"lab_name": "Troponin", "pattern": "elevated", "typical_range": ">0.04 ng/mL"}
        ],
        critical_exam_findings=["S3 gallop", "diaphoresis"],
        symptom_timeline="acute",
        risk_factors=["hypertension", "diabetes", "smoking"],
        age_range=(40, 80),
        valid_genders=["M", "F"],
        common_differentials=["unstable angina", "pericarditis"],
        distinguishing_features=["ST elevation on ECG", "elevated troponin"]
    )
    assert template.primary_diagnosis == "Acute Myocardial Infarction"
    assert template.diagnosis_category == "cardiac"
    assert len(template.cardinal_symptoms) == 2


def test_variation_parameters_defaults():
    params = VariationParameters()
    assert params.age is None
    assert params.gender is None
    assert params.symptom_severity == "typical"
    assert params.atypical_presentation is False
    assert params.add_red_herrings is False
    assert params.lab_variation == "normal"


def test_variation_parameters_custom():
    params = VariationParameters(
        age=65,
        gender="F",
        add_comorbidities=["COPD", "CKD"],
        symptom_severity="severe",
        atypical_presentation=True
    )
    assert params.age == 65
    assert params.gender == "F"
    assert params.add_comorbidities == ["COPD", "CKD"]
    assert params.symptom_severity == "severe"


def test_validation_result_valid():
    result = ValidationResult(
        is_valid=True,
        issues=[],
        confidence_score=0.95
    )
    assert result.is_valid is True
    assert len(result.issues) == 0


def test_validation_result_with_issues():
    issues = [
        ValidationIssue(
            field="vitals.heart_rate",
            message="Heart rate 250 exceeds critical high of 200",
            severity=ValidationSeverity.ERROR
        ),
        ValidationIssue(
            field="labs.troponin",
            message="Troponin value borderline",
            severity=ValidationSeverity.WARNING
        )
    ]
    result = ValidationResult(
        is_valid=False,
        issues=issues,
        confidence_score=0.3
    )
    assert result.is_valid is False
    assert len(result.issues) == 2
    assert result.issues[0].severity == ValidationSeverity.ERROR


def test_validation_severity_enum():
    assert ValidationSeverity.ERROR.value == "error"
    assert ValidationSeverity.WARNING.value == "warning"
    assert ValidationSeverity.INFO.value == "info"
