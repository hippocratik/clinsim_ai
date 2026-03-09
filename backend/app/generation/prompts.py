"""Centralized prompts for the case generation pipeline.

This module consolidates all LLM prompts used in case generation,
template extraction, and validation for easier maintenance and consistency.
"""

# Re-export prompts from their source modules for backward compatibility
from app.generation.template_extractor import TEMPLATE_EXTRACTION_SYSTEM_PROMPT
from app.generation.variation_generator import VARIATION_GENERATION_SYSTEM_PROMPT
from app.generation.clinical_validator import CLINICAL_VALIDATION_SYSTEM_PROMPT

__all__ = [
    "TEMPLATE_EXTRACTION_SYSTEM_PROMPT",
    "VARIATION_GENERATION_SYSTEM_PROMPT",
    "CLINICAL_VALIDATION_SYSTEM_PROMPT",
]
