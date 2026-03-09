import pytest
from app.prompts.patient_dialogue import (
    classify_question,
    build_patient_prompt,
    format_context_chunks,
    format_conversation_history,
    PATIENT_SYSTEM_PROMPT,
    PATIENT_USER_TEMPLATE,
)


def test_classify_pain_question():
    chunk_types = classify_question("Where does it hurt?")
    assert "presenting_complaint" in chunk_types or "hpi" in chunk_types


def test_classify_medication_question():
    chunk_types = classify_question("What medications are you taking?")
    assert "medications" in chunk_types


def test_classify_history_question():
    chunk_types = classify_question("Do you have any past medical history?")
    assert "pmh" in chunk_types


def test_classify_onset_question():
    chunk_types = classify_question("When did the symptoms start?")
    assert "hpi" in chunk_types or "presenting_complaint" in chunk_types


def test_classify_default_returns_list():
    chunk_types = classify_question("Tell me about yourself")
    assert isinstance(chunk_types, list)
    assert len(chunk_types) > 0


def test_format_context_chunks_with_objects():
    from dataclasses import dataclass

    @dataclass
    class FakeChunk:
        chunk_type: str
        content: str

    chunks = [FakeChunk("presenting_complaint", "Chest pain"), FakeChunk("hpi", "Started 3 hours ago")]
    result = format_context_chunks(chunks)
    assert "PRESENTING_COMPLAINT" in result
    assert "Chest pain" in result
    assert "HPI" in result


def test_format_context_chunks_empty():
    result = format_context_chunks([])
    assert "No relevant context" in result


def test_format_conversation_history_empty():
    result = format_conversation_history([])
    assert "No previous conversation" in result


def test_build_patient_prompt_contains_question():
    prompt = build_patient_prompt(
        chunks=[],
        chat_history=[],
        trainee_question="How long have you had this pain?",
    )
    assert "How long have you had this pain?" in prompt


def test_system_prompt_contains_critical_rules():
    assert "ONLY" in PATIENT_SYSTEM_PROMPT
    assert "diagnosis" in PATIENT_SYSTEM_PROMPT.lower()
    assert "first person" in PATIENT_SYSTEM_PROMPT.lower()


def test_user_template_has_required_placeholders():
    assert "{context_chunks}" in PATIENT_USER_TEMPLATE
    assert "{conversation_history}" in PATIENT_USER_TEMPLATE
    assert "{trainee_question}" in PATIENT_USER_TEMPLATE