"""Template extraction from clinical cases using LLM."""
import json
from app.models import Case
from app.generation.models import ClinicalTemplate


TEMPLATE_EXTRACTION_SYSTEM_PROMPT = """You are a clinical expert tasked with extracting a reusable clinical template from a patient case.

Analyze the provided case and extract a structured template that captures the essential clinical pattern.

Your response must be valid JSON with the following fields:
- primary_diagnosis: The main diagnosis (string)
- icd9_code: The ICD-9 code for the diagnosis (string)
- diagnosis_category: Category like cardiac, respiratory, infectious, neurological, etc. (string)
- cardinal_symptoms: Must-have symptoms for this diagnosis (list of strings)
- supporting_symptoms: Common but optional symptoms (list of strings)
- critical_lab_patterns: List of objects with lab_name, pattern (elevated/decreased/normal), typical_range
- critical_exam_findings: Physical exam findings essential for diagnosis (list of strings)
- symptom_timeline: One of hyperacute, acute, subacute, chronic (string)
- risk_factors: Common risk factors for this condition (list of strings)
- age_range: Typical age range as [min_age, max_age] (list of two integers)
- valid_genders: Which genders can have this condition ["M", "F"] or ["M"] or ["F"] (list)
- common_differentials: Other diagnoses to consider (list of strings)
- distinguishing_features: Features that distinguish this from differentials (list of strings)

Return ONLY valid JSON, no markdown formatting or explanation."""


class TemplateExtractor:
    """Extracts clinical templates from source cases using LLM."""

    def __init__(self, llm_service):
        """Initialize with an LLM service.

        Args:
            llm_service: Service with async generate() method for LLM calls
        """
        self.llm_service = llm_service

    async def extract_template(self, case: Case) -> ClinicalTemplate:
        """Extract a clinical template from a case.

        Args:
            case: The source case to extract template from

        Returns:
            ClinicalTemplate with extracted clinical patterns
        """
        # Build case summary for LLM
        case_summary = self._build_case_summary(case)

        # Call LLM to extract template
        llm_response = await self.llm_service.generate(
            prompt=case_summary,
            system_prompt=TEMPLATE_EXTRACTION_SYSTEM_PROMPT
        )

        # Parse response and build template
        template_data = json.loads(llm_response)

        return ClinicalTemplate(
            source_case_id=case.case_id,
            primary_diagnosis=template_data["primary_diagnosis"],
            icd9_code=template_data["icd9_code"],
            diagnosis_category=template_data["diagnosis_category"],
            cardinal_symptoms=template_data["cardinal_symptoms"],
            supporting_symptoms=template_data["supporting_symptoms"],
            critical_lab_patterns=template_data["critical_lab_patterns"],
            critical_exam_findings=template_data["critical_exam_findings"],
            symptom_timeline=template_data["symptom_timeline"],
            risk_factors=template_data["risk_factors"],
            age_range=tuple(template_data["age_range"]),
            valid_genders=template_data["valid_genders"],
            common_differentials=template_data["common_differentials"],
            distinguishing_features=template_data["distinguishing_features"]
        )

    def _build_case_summary(self, case: Case) -> str:
        """Build a text summary of the case for LLM processing."""
        parts = [
            f"Case ID: {case.case_id}",
            f"Demographics: {case.demographics.age}yo {case.demographics.gender}, {case.demographics.admission_type}",
            f"Presenting Complaint: {case.presenting_complaint}",
            f"History of Present Illness: {case.hpi}",
        ]

        if case.past_medical_history:
            parts.append(f"Past Medical History: {', '.join(case.past_medical_history)}")

        if case.medications:
            parts.append(f"Medications: {', '.join(case.medications)}")

        if case.allergies:
            parts.append(f"Allergies: {', '.join(case.allergies)}")

        if case.physical_exam:
            vitals = case.physical_exam.vitals
            parts.append(f"Vitals: HR {vitals.heart_rate}, BP {vitals.blood_pressure}, "
                        f"RR {vitals.respiratory_rate}, T {vitals.temperature}, SpO2 {vitals.spo2}")
            if case.physical_exam.findings:
                parts.append(f"Exam Findings: {case.physical_exam.findings}")

        if case.available_labs:
            lab_strs = [f"{lab.lab_name}: {lab.value} {lab.unit} ({lab.flag})"
                       for lab in case.available_labs]
            parts.append(f"Labs: {'; '.join(lab_strs)}")

        if case.diagnoses:
            diag_strs = [f"{d.description} ({d.icd9_code})" for d in case.diagnoses]
            parts.append(f"Diagnoses: {', '.join(diag_strs)}")

        return "\n".join(parts)
