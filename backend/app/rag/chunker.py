from app.models import Case, CaseChunk

def chunk_case(case: Case) -> list[CaseChunk]:
    """Split a case into semantic chunks for RAG retrieval."""
    chunks = []

    base_metadata = {
        "subject_id": case.subject_id,
        "hadm_id": case.hadm_id,
        "icd9_codes": [d.icd9_code for d in case.diagnoses]
    }

    # Chunk 1: Presenting complaint + HPI
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_presenting",
        case_id=case.case_id,
        chunk_type="presenting_complaint",
        content=f"Chief complaint: {case.presenting_complaint}\n\nHistory of present illness: {case.hpi}",
        metadata=base_metadata.copy()
    ))

    # Chunk 2: Past medical history
    pmh_text = ", ".join(case.past_medical_history) if case.past_medical_history else "No significant past medical history"
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_pmh",
        case_id=case.case_id,
        chunk_type="pmh",
        content=f"Past medical history: {pmh_text}",
        metadata=base_metadata.copy()
    ))

    # Chunk 3: Physical exam
    vitals = case.physical_exam.vitals
    vitals_text = f"HR: {vitals.heart_rate}, BP: {vitals.blood_pressure}, RR: {vitals.respiratory_rate}, Temp: {vitals.temperature}°C, SpO2: {vitals.spo2}%"
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_exam",
        case_id=case.case_id,
        chunk_type="physical_exam",
        content=f"Vital signs: {vitals_text}\n\nPhysical exam findings: {case.physical_exam.findings}",
        metadata=base_metadata.copy()
    ))

    # Chunk 4: Labs
    lab_lines = [f"- {lab.lab_name}: {lab.value} {lab.unit} ({lab.flag})" for lab in case.available_labs]
    lab_text = "\n".join(lab_lines) if lab_lines else "No lab results available"
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_labs",
        case_id=case.case_id,
        chunk_type="labs",
        content=f"Laboratory results:\n{lab_text}",
        metadata=base_metadata.copy()
    ))

    # Chunk 5: Medications
    meds_text = ", ".join(case.medications) if case.medications else "No current medications"
    allergies_text = ", ".join(case.allergies) if case.allergies else "No known allergies"
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_meds",
        case_id=case.case_id,
        chunk_type="medications",
        content=f"Current medications: {meds_text}\nAllergies: {allergies_text}",
        metadata=base_metadata.copy()
    ))

    # Chunk 6: Diagnosis
    diag_lines = []
    for d in case.diagnoses:
        prefix = "[PRIMARY] " if d.is_primary else ""
        diag_lines.append(f"{prefix}{d.description} (ICD-9: {d.icd9_code})")
    diag_text = "\n".join(diag_lines)
    chunks.append(CaseChunk(
        chunk_id=f"{case.case_id}_diagnosis",
        case_id=case.case_id,
        chunk_type="diagnosis",
        content=f"Diagnoses:\n{diag_text}",
        metadata=base_metadata.copy()
    ))

    return chunks
