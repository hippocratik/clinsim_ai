import json
from typing import Optional
from app.core.llm import LLMService
from app.models import Case, Demographics, PhysicalExam, Vitals, LabResult, Diagnosis
from app.prompts.discharge_parser import DISCHARGE_PARSER_SYSTEM_PROMPT, format_parser_prompt

async def parse_discharge_summary(
    llm_service: LLMService,
    discharge_summary: str
) -> dict:
    """Parse a discharge summary into structured data using Claude."""

    response = await llm_service.generate(
        system_prompt=DISCHARGE_PARSER_SYSTEM_PROMPT,
        user_prompt=format_parser_prompt(discharge_summary),
        max_tokens=2000
    )

    # Parse JSON response
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        # Try to extract JSON from response if wrapped in markdown
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            raise ValueError(f"Failed to parse LLM response as JSON: {response[:200]}")

    return parsed

def build_case_from_parsed(
    parsed: dict,
    subject_id: int,
    hadm_id: int,
    diagnoses: list[dict],
    labs: list[dict],
    prescriptions: list[dict],
    age: int,
    gender: str,
    admission_type: str = "EMERGENCY"
) -> Case:
    """Build a Case object from parsed discharge summary and linked data."""

    # Build vitals
    vitals_data = parsed.get("physical_exam", {}).get("vitals", {})
    vitals = Vitals(
        heart_rate=vitals_data.get("heart_rate"),
        blood_pressure=vitals_data.get("blood_pressure"),
        respiratory_rate=vitals_data.get("respiratory_rate"),
        temperature=vitals_data.get("temperature"),
        spo2=vitals_data.get("spo2")
    )

    # Build physical exam
    physical_exam = PhysicalExam(
        vitals=vitals,
        findings=parsed.get("physical_exam", {}).get("findings", "")
    )

    # Build lab results
    lab_results = []
    for lab in labs:
        flag = "normal"
        if lab.get("flag") == "abnormal":
            # Determine if high or low based on common patterns
            flag = "high"  # Simplified - would need reference ranges

        unit = lab.get("valueuom", lab.get("unit", "")) or ""
        # pandas reads missing values as float NaN - coerce to empty string
        if not isinstance(unit, str):
            unit = ""
        lab_results.append(LabResult(
            lab_name=lab.get("label", lab.get("lab_name", "Unknown")),
            value=str(lab.get("value", "")),
            unit=unit,
            flag=flag
        ))

    # Build diagnoses
    diagnosis_list = []
    for i, diag in enumerate(diagnoses):
        diagnosis_list.append(Diagnosis(
            icd9_code=diag.get("icd9_code", ""),
            description=diag.get("description", diag.get("long_title", "")),
            is_primary=(diag.get("seq_num", i+1) == 1)
        ))

    # Determine difficulty based on number of diagnoses
    difficulty = "easy" if len(diagnosis_list) <= 2 else "medium" if len(diagnosis_list) <= 4 else "hard"

    # Determine specialties from diagnosis descriptions
    specialties = _infer_specialties(diagnosis_list)

    return Case(
        case_id=f"case_{hadm_id}",
        subject_id=subject_id,
        hadm_id=hadm_id,
        demographics=Demographics(
            age=age,
            gender=gender,
            admission_type=admission_type
        ),
        presenting_complaint=parsed.get("presenting_complaint", ""),
        hpi=parsed.get("hpi", ""),
        past_medical_history=parsed.get("past_medical_history", []),
        medications=_merge_medications(parsed.get("medications", []), prescriptions),
        allergies=parsed.get("allergies", []),
        physical_exam=physical_exam,
        available_labs=lab_results,
        diagnoses=diagnosis_list,
        discharge_summary=parsed.get("hospital_course", ""),
        difficulty=difficulty,
        specialties=specialties,
        is_generated=False
    )

def _merge_medications(parsed_meds: list, prescriptions: list[dict]) -> list:
    """Merge LLM-parsed medication names with structured prescriptions table data.

    Returns a unified list: starts from parsed_meds (strings from discharge
    summary) and appends any drug names from prescriptions not already present.
    """
    existing = {m.lower() if isinstance(m, str) else str(m).lower() for m in parsed_meds}
    merged = list(parsed_meds)
    for rx in prescriptions:
        drug = rx.get("drug", "")
        if drug and drug.lower() not in existing:
            merged.append(drug)
            existing.add(drug.lower())
    return merged


def _infer_specialties(diagnoses: list[Diagnosis]) -> list[str]:
    """Infer medical specialties from diagnosis descriptions."""
    specialties = set()

    keywords = {
        "cardiology": ["heart", "cardiac", "infarction", "angina", "arrhythmia", "coronary"],
        "pulmonology": ["lung", "pulmonary", "pneumonia", "copd", "respiratory", "asthma"],
        "infectious": ["sepsis", "infection", "bacterial", "viral", "abscess"],
        "neurology": ["stroke", "seizure", "neurological", "brain", "cva"],
        "gastroenterology": ["liver", "hepatic", "gi", "gastro", "bowel", "intestinal"],
        "nephrology": ["kidney", "renal", "dialysis"],
        "endocrinology": ["diabetes", "thyroid", "endocrine", "diabetic"]
    }

    for diag in diagnoses:
        desc_lower = diag.description.lower()
        for specialty, terms in keywords.items():
            if any(term in desc_lower for term in terms):
                specialties.add(specialty)

    return list(specialties) if specialties else ["general"]
