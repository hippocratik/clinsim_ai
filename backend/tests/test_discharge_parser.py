import pytest
from app.prompts.discharge_parser import (
    DISCHARGE_PARSER_SYSTEM_PROMPT,
    DISCHARGE_PARSER_USER_TEMPLATE,
    format_parser_prompt
)

def test_system_prompt_contains_schema():
    assert "presenting_complaint" in DISCHARGE_PARSER_SYSTEM_PROMPT
    assert "past_medical_history" in DISCHARGE_PARSER_SYSTEM_PROMPT
    assert "physical_exam" in DISCHARGE_PARSER_SYSTEM_PROMPT
    assert "JSON" in DISCHARGE_PARSER_SYSTEM_PROMPT

def test_user_template_has_placeholder():
    assert "{discharge_summary}" in DISCHARGE_PARSER_USER_TEMPLATE

def test_format_parser_prompt():
    result = format_parser_prompt("Patient presents with chest pain...")
    assert "Patient presents with chest pain" in result
    assert "<discharge_summary>" in result
