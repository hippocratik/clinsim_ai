from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ValidationSeverity(Enum):
    ERROR = "error"      # Reject case
    WARNING = "warning"  # Usable but flagged
    INFO = "info"        # Minor observation


@dataclass
class ClinicalTemplate:
    """Extracted clinical pattern from a source case."""
    source_case_id: str
    primary_diagnosis: str
    icd9_code: str
    diagnosis_category: str  # cardiac, respiratory, infectious, neurological, etc.
    cardinal_symptoms: list[str]       # Must-have symptoms
    supporting_symptoms: list[str]     # Common but optional
    critical_lab_patterns: list[dict]  # {"lab_name": str, "pattern": str, "typical_range": str}
    critical_exam_findings: list[str]
    symptom_timeline: str              # hyperacute, acute, subacute, chronic
    risk_factors: list[str]
    age_range: tuple[int, int]
    valid_genders: list[str]
    common_differentials: list[str]
    distinguishing_features: list[str]


@dataclass
class VariationParameters:
    """Parameters to control case variation generation."""
    age: Optional[int] = None
    gender: Optional[str] = None
    add_comorbidities: list[str] = field(default_factory=list)
    symptom_severity: str = "typical"    # mild, typical, severe
    atypical_presentation: bool = False
    add_red_herrings: bool = False
    lab_variation: str = "normal"        # normal, borderline, extreme


@dataclass
class ValidationIssue:
    """A single validation issue found in a generated case."""
    field: str
    message: str
    severity: ValidationSeverity


@dataclass
class ValidationResult:
    """Result of validating a generated case."""
    is_valid: bool
    issues: list[ValidationIssue]
    confidence_score: float  # 0.0 to 1.0
