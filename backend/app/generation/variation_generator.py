"""Variation generator for creating novel clinical cases from templates."""
import json
from app.generation.models import ClinicalTemplate, VariationParameters


VARIATION_GENERATION_SYSTEM_PROMPT = """You are a clinical case generator for medical education. Given a clinical template and reference cases, generate a novel but clinically plausible patient case.

CRITICAL RULES:
1. The generated case MUST have the same underlying diagnosis as the template
2. All symptoms, labs, and findings must be clinically plausible
3. Use reference cases for realistic lab values and presentations
4. The case should be DIFFERENT from the source
5. Never invent lab values outside realistic ranges
6. Maintain internal consistency

OUTPUT FORMAT: Valid JSON matching the Case schema with the following structure:
{
    "case_id": "string - unique identifier",
    "subject_id": number,
    "hadm_id": number,
    "demographics": {
        "age": number,
        "gender": "M" or "F",
        "admission_type": "EMERGENCY" or "ELECTIVE" or "URGENT"
    },
    "presenting_complaint": "string - chief complaint",
    "hpi": "string - history of present illness",
    "past_medical_history": ["array of conditions"],
    "medications": ["array of medications"],
    "allergies": ["array of allergies"],
    "physical_exam": {
        "vitals": {
            "heart_rate": number,
            "blood_pressure": "string like '120/80'",
            "respiratory_rate": number,
            "temperature": number,
            "spo2": number
        },
        "findings": "string - physical exam findings"
    },
    "available_labs": [
        {"lab_name": "string", "value": "string", "unit": "string", "flag": "normal" or "abnormal" or "critical"}
    ],
    "diagnoses": [
        {"icd9_code": "string", "description": "string", "is_primary": boolean}
    ],
    "discharge_summary": "string",
    "difficulty": "easy" or "medium" or "hard",
    "specialties": ["array of specialties"],
    "is_generated": true
}

Return ONLY valid JSON, no markdown or explanation."""


class VariationGenerator:
    """Generates variations of clinical cases from templates using LLM and RAG."""

    def __init__(self, llm_service, rag_service):
        """Initialize with LLM and RAG services.

        Args:
            llm_service: Service with async generate() method for LLM calls
            rag_service: Service with async search() method for RAG retrieval
        """
        self.llm = llm_service
        self.rag = rag_service

    async def generate_variation(
        self,
        template: ClinicalTemplate,
        params: VariationParameters = None
    ) -> dict:
        """Generate a novel case variation from a template.

        Args:
            template: The clinical template to base the case on
            params: Optional parameters to control variation

        Returns:
            Dictionary representing a complete Case
        """
        # 1. Retrieve similar real cases for grounding
        rag_query = f"{template.primary_diagnosis} {template.diagnosis_category}"
        similar_cases = await self.rag.search(rag_query)

        # 2. Build prompt with template and reference cases
        prompt = self._build_generation_prompt(template, similar_cases, params)

        # 3. Generate variation with LLM
        llm_response = await self.llm.generate(
            prompt=prompt,
            system_prompt=VARIATION_GENERATION_SYSTEM_PROMPT
        )

        # 4. Parse and return case dict
        return json.loads(llm_response)

    async def generate_batch(
        self,
        template: ClinicalTemplate,
        count: int = 3
    ) -> list[dict]:
        """Generate multiple case variations from a template.

        Args:
            template: The clinical template to base cases on
            count: Number of variations to generate

        Returns:
            List of dictionaries representing Cases
        """
        results = []
        for _ in range(count):
            case = await self.generate_variation(template)
            results.append(case)
        return results

    def _build_generation_prompt(
        self,
        template: ClinicalTemplate,
        similar_cases: list[dict],
        params: VariationParameters = None
    ) -> str:
        """Build the user prompt for case generation."""
        parts = [
            "Generate a novel clinical case based on the following template:",
            "",
            f"PRIMARY DIAGNOSIS: {template.primary_diagnosis} ({template.icd9_code})",
            f"CATEGORY: {template.diagnosis_category}",
            f"SYMPTOM TIMELINE: {template.symptom_timeline}",
            "",
            f"CARDINAL SYMPTOMS (must include): {', '.join(template.cardinal_symptoms)}",
            f"SUPPORTING SYMPTOMS (may include): {', '.join(template.supporting_symptoms)}",
            "",
            f"CRITICAL LAB PATTERNS:",
        ]

        for lab in template.critical_lab_patterns:
            parts.append(f"  - {lab['lab_name']}: {lab['pattern']} ({lab.get('typical_range', 'N/A')})")

        parts.extend([
            "",
            f"CRITICAL EXAM FINDINGS: {', '.join(template.critical_exam_findings)}",
            f"RISK FACTORS: {', '.join(template.risk_factors)}",
            f"AGE RANGE: {template.age_range[0]}-{template.age_range[1]} years",
            f"VALID GENDERS: {', '.join(template.valid_genders)}",
            "",
            "REFERENCE CASES FOR GROUNDING:"
        ])

        for ref in similar_cases[:3]:
            parts.append(f"  - {ref.get('content', 'No content')}")

        # Add variation parameters if provided
        if params:
            parts.extend([
                "",
                "SPECIFIC REQUIREMENTS FOR THIS VARIATION:"
            ])
            if params.age is not None:
                parts.append(f"  - Patient age: {params.age}")
            if params.gender is not None:
                parts.append(f"  - Patient gender: {params.gender}")
            if params.add_comorbidities:
                parts.append(f"  - Include comorbidities: {', '.join(params.add_comorbidities)}")
            if params.symptom_severity != "typical":
                parts.append(f"  - Symptom severity: {params.symptom_severity}")
            if params.atypical_presentation:
                parts.append("  - Create an atypical presentation of this diagnosis")
            if params.add_red_herrings:
                parts.append("  - Include clinically plausible red herrings")
            if params.lab_variation != "normal":
                parts.append(f"  - Lab value variation: {params.lab_variation}")

        parts.extend([
            "",
            "Generate a complete, clinically plausible case that is DIFFERENT from the source but has the same underlying diagnosis."
        ])

        return "\n".join(parts)
