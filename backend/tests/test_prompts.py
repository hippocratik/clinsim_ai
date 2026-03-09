"""Tests for centralized prompts module."""
import pytest
from app.generation.prompts import (
    TEMPLATE_EXTRACTION_SYSTEM_PROMPT,
    VARIATION_GENERATION_SYSTEM_PROMPT,
    CLINICAL_VALIDATION_SYSTEM_PROMPT,
)


def test_all_prompts_are_exported():
    """Verify all prompts are accessible from the centralized module."""
    assert TEMPLATE_EXTRACTION_SYSTEM_PROMPT is not None
    assert VARIATION_GENERATION_SYSTEM_PROMPT is not None
    assert CLINICAL_VALIDATION_SYSTEM_PROMPT is not None


def test_all_prompts_are_non_empty_strings():
    """Verify all prompts are meaningful strings."""
    prompts = [
        TEMPLATE_EXTRACTION_SYSTEM_PROMPT,
        VARIATION_GENERATION_SYSTEM_PROMPT,
        CLINICAL_VALIDATION_SYSTEM_PROMPT,
    ]
    for prompt in prompts:
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Prompts should be substantial


def test_all_prompts_request_json_output():
    """Verify all prompts request JSON output format."""
    prompts = [
        TEMPLATE_EXTRACTION_SYSTEM_PROMPT,
        VARIATION_GENERATION_SYSTEM_PROMPT,
        CLINICAL_VALIDATION_SYSTEM_PROMPT,
    ]
    for prompt in prompts:
        assert "JSON" in prompt


def test_prompts_have_consistent_style():
    """Verify prompts follow consistent formatting patterns."""
    prompts = [
        TEMPLATE_EXTRACTION_SYSTEM_PROMPT,
        VARIATION_GENERATION_SYSTEM_PROMPT,
        CLINICAL_VALIDATION_SYSTEM_PROMPT,
    ]
    for prompt in prompts:
        # All should end with instruction about JSON-only output
        assert "JSON" in prompt.upper()
        # All should have clear role definition
        assert "you" in prompt.lower() or "You" in prompt
