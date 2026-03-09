"""Clinical validation for generated cases."""
import json
from typing import Optional
from app.generation.models import (
    ClinicalTemplate,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity
)


CLINICAL_VALIDATION_SYSTEM_PROMPT = """You are a clinical expert validating AI-generated patient cases for medical education.

Assess whether the provided case is clinically plausible given the expected diagnosis and template.

Check for:
1. Internal consistency (symptoms match diagnosis, labs match clinical picture)
2. Missing cardinal symptoms that should be present
3. Contradictory findings
4. Unrealistic combinations of values
5. Age/gender appropriateness for the diagnosis

Return your assessment as JSON:
{
    "is_clinically_plausible": boolean,
    "issues": [
        {
            "field": "string - affected field",
            "message": "string - description of issue",
            "severity": "error" or "warning" or "info"
        }
    ],
    "confidence": float (0.0 to 1.0)
}

Return ONLY valid JSON, no explanation."""


class ClinicalValidator:
    """Validates generated clinical cases using rule-based and LLM checks."""

    # Reference ranges for rule-based validation
    LAB_REFERENCE_RANGES = {
        "troponin": {"low": 0, "high": 0.04, "critical_high": 2.0, "unit": "ng/mL"},
        "bnp": {"low": 0, "high": 100, "critical_high": 5000, "unit": "pg/mL"},
        "creatinine": {"low": 0.6, "high": 1.2, "critical_high": 10.0, "unit": "mg/dL"},
        "potassium": {"low": 3.5, "high": 5.0, "critical_low": 2.5, "critical_high": 6.5, "unit": "mEq/L"},
        "sodium": {"low": 136, "high": 145, "critical_low": 120, "critical_high": 160, "unit": "mEq/L"},
        "glucose": {"low": 70, "high": 100, "critical_low": 40, "critical_high": 500, "unit": "mg/dL"},
        "hemoglobin": {"low": 12.0, "high": 17.5, "critical_low": 7.0, "critical_high": 20.0, "unit": "g/dL"},
        "wbc": {"low": 4.5, "high": 11.0, "critical_low": 2.0, "critical_high": 30.0, "unit": "K/uL"},
        "platelets": {"low": 150, "high": 400, "critical_low": 50, "critical_high": 1000, "unit": "K/uL"},
    }

    VITAL_RANGES = {
        "heart_rate": {"low": 60, "high": 100, "critical_low": 30, "critical_high": 200},
        "blood_pressure_systolic": {"low": 90, "high": 140, "critical_low": 70, "critical_high": 220},
        "blood_pressure_diastolic": {"low": 60, "high": 90, "critical_low": 40, "critical_high": 130},
        "respiratory_rate": {"low": 12, "high": 20, "critical_low": 8, "critical_high": 40},
        "temperature": {"low": 36.1, "high": 37.2, "critical_low": 32.0, "critical_high": 42.0},
        "spo2": {"low": 95, "high": 100, "critical_low": 85, "critical_high": 100},
    }

    def __init__(self, llm_service=None):
        """Initialize validator with optional LLM service.

        Args:
            llm_service: Optional service with async generate() method for LLM validation
        """
        self.llm_service = llm_service

    async def validate(
        self,
        generated_case: dict,
        template: ClinicalTemplate
    ) -> ValidationResult:
        """Validate a generated case against clinical rules and template.

        Args:
            generated_case: Dictionary representing the generated case
            template: The clinical template used to generate the case

        Returns:
            ValidationResult with issues and validity status
        """
        issues = []

        # Rule-based validation
        issues.extend(self._validate_vitals(generated_case))
        issues.extend(self._validate_labs(generated_case))
        issues.extend(self._validate_demographics(generated_case, template))

        # LLM-based validation if service available
        if self.llm_service:
            issues.extend(await self._llm_validate(generated_case, template))

        # Calculate confidence score
        confidence_score = self._calculate_confidence(issues)

        # Determine validity - no errors means valid
        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            confidence_score=confidence_score
        )

    def _validate_vitals(self, case: dict) -> list[ValidationIssue]:
        """Validate vital signs are within plausible ranges."""
        issues = []

        vitals = case.get("physical_exam", {}).get("vitals", {})
        if not vitals:
            return issues

        # Heart rate
        hr = vitals.get("heart_rate")
        if hr is not None:
            issues.extend(self._check_range("vitals.heart_rate", hr, self.VITAL_RANGES["heart_rate"]))

        # Blood pressure
        bp = vitals.get("blood_pressure")
        if bp and "/" in str(bp):
            try:
                systolic, diastolic = map(int, str(bp).split("/"))
                issues.extend(self._check_range("vitals.blood_pressure_systolic", systolic,
                                               self.VITAL_RANGES["blood_pressure_systolic"]))
                issues.extend(self._check_range("vitals.blood_pressure_diastolic", diastolic,
                                               self.VITAL_RANGES["blood_pressure_diastolic"]))
            except ValueError:
                issues.append(ValidationIssue(
                    field="vitals.blood_pressure",
                    message=f"Invalid blood pressure format: {bp}",
                    severity=ValidationSeverity.WARNING
                ))

        # Respiratory rate
        rr = vitals.get("respiratory_rate")
        if rr is not None:
            issues.extend(self._check_range("vitals.respiratory_rate", rr, self.VITAL_RANGES["respiratory_rate"]))

        # Temperature
        temp = vitals.get("temperature")
        if temp is not None:
            issues.extend(self._check_range("vitals.temperature", temp, self.VITAL_RANGES["temperature"]))

        # SpO2
        spo2 = vitals.get("spo2")
        if spo2 is not None:
            issues.extend(self._check_range("vitals.spo2", spo2, self.VITAL_RANGES["spo2"]))

        return issues

    def _validate_labs(self, case: dict) -> list[ValidationIssue]:
        """Validate lab values are within plausible ranges."""
        issues = []

        labs = case.get("available_labs", [])
        for lab in labs:
            lab_name = lab.get("lab_name", "").lower()
            value_str = lab.get("value", "")

            # Try to parse numeric value
            try:
                value = float(value_str.replace("<", "").replace(">", ""))
            except (ValueError, AttributeError):
                continue

            # Check against reference ranges if we have them
            if lab_name in self.LAB_REFERENCE_RANGES:
                ranges = self.LAB_REFERENCE_RANGES[lab_name]
                issues.extend(self._check_range(f"labs.{lab_name}", value, ranges))

        return issues

    def _validate_demographics(
        self,
        case: dict,
        template: ClinicalTemplate
    ) -> list[ValidationIssue]:
        """Validate demographics match template expectations."""
        issues = []

        demographics = case.get("demographics", {})

        # Age validation
        age = demographics.get("age")
        if age is not None:
            min_age, max_age = template.age_range
            if age < min_age or age > max_age:
                issues.append(ValidationIssue(
                    field="demographics.age",
                    message=f"Age {age} outside expected range {min_age}-{max_age} for {template.primary_diagnosis}",
                    severity=ValidationSeverity.WARNING
                ))

        # Gender validation
        gender = demographics.get("gender")
        if gender is not None:
            if gender not in template.valid_genders:
                issues.append(ValidationIssue(
                    field="demographics.gender",
                    message=f"Gender {gender} not valid for {template.primary_diagnosis}. Expected: {template.valid_genders}",
                    severity=ValidationSeverity.ERROR
                ))

        return issues

    async def _llm_validate(
        self,
        case: dict,
        template: ClinicalTemplate
    ) -> list[ValidationIssue]:
        """Use LLM to check clinical plausibility."""
        issues = []

        prompt = self._build_validation_prompt(case, template)

        response = await self.llm_service.generate(
            prompt=prompt,
            system_prompt=CLINICAL_VALIDATION_SYSTEM_PROMPT
        )

        try:
            result = json.loads(response)

            # Convert LLM issues to ValidationIssue objects
            for llm_issue in result.get("issues", []):
                severity_str = llm_issue.get("severity", "warning").lower()
                severity = {
                    "error": ValidationSeverity.ERROR,
                    "warning": ValidationSeverity.WARNING,
                    "info": ValidationSeverity.INFO
                }.get(severity_str, ValidationSeverity.WARNING)

                issues.append(ValidationIssue(
                    field=llm_issue.get("field", "unknown"),
                    message=llm_issue.get("message", ""),
                    severity=severity
                ))

        except json.JSONDecodeError:
            issues.append(ValidationIssue(
                field="llm_validation",
                message="Failed to parse LLM validation response",
                severity=ValidationSeverity.WARNING
            ))

        return issues

    def _check_range(self, field: str, value: float, ranges: dict) -> list[ValidationIssue]:
        """Check if a value is within specified ranges."""
        issues = []

        # Check critical ranges first
        critical_low = ranges.get("critical_low")
        critical_high = ranges.get("critical_high")

        if critical_low is not None and value < critical_low:
            issues.append(ValidationIssue(
                field=field,
                message=f"Value {value} below critical low ({critical_low})",
                severity=ValidationSeverity.ERROR
            ))
        elif critical_high is not None and value > critical_high:
            issues.append(ValidationIssue(
                field=field,
                message=f"Value {value} exceeds critical high ({critical_high})",
                severity=ValidationSeverity.ERROR
            ))
        elif value < ranges.get("low", float("-inf")):
            issues.append(ValidationIssue(
                field=field,
                message=f"Value {value} below normal range ({ranges.get('low')})",
                severity=ValidationSeverity.INFO
            ))
        elif value > ranges.get("high", float("inf")):
            issues.append(ValidationIssue(
                field=field,
                message=f"Value {value} above normal range ({ranges.get('high')})",
                severity=ValidationSeverity.INFO
            ))

        return issues

    def _build_validation_prompt(self, case: dict, template: ClinicalTemplate) -> str:
        """Build prompt for LLM validation."""
        return f"""Validate this generated clinical case:

EXPECTED DIAGNOSIS: {template.primary_diagnosis} ({template.icd9_code})
CATEGORY: {template.diagnosis_category}
CARDINAL SYMPTOMS: {', '.join(template.cardinal_symptoms)}
EXPECTED AGE RANGE: {template.age_range[0]}-{template.age_range[1]}

GENERATED CASE:
{json.dumps(case, indent=2)}

Assess clinical plausibility and identify any issues."""

    def _calculate_confidence(self, issues: list[ValidationIssue]) -> float:
        """Calculate confidence score based on issues found."""
        if not issues:
            return 1.0

        # Deduct points based on severity
        penalties = {
            ValidationSeverity.ERROR: 0.3,
            ValidationSeverity.WARNING: 0.1,
            ValidationSeverity.INFO: 0.02
        }

        total_penalty = sum(penalties.get(i.severity, 0) for i in issues)
        return max(0.0, 1.0 - total_penalty)
