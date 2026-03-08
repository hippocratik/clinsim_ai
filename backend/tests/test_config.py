import pytest
import os

def test_settings_loads_defaults():
    from app.config import Settings

    settings = Settings(anthropic_api_key="test-key")

    assert settings.cases_path == "data/cases.json"
    assert settings.chunks_path == "data/chunks.json"
    assert settings.faiss_index_path == "data/faiss.index"
    assert settings.rag_top_k == 5
    assert settings.embedding_model == "all-MiniLM-L6-v2"
    assert settings.llm_model == "claude-opus-4-5-20251101"
    assert settings.default_resource_budget == 100

def test_settings_requires_api_key():
    from app.config import Settings
    from pydantic import ValidationError

    # Clear any env var
    os.environ.pop("ANTHROPIC_API_KEY", None)

    with pytest.raises(ValidationError):
        Settings()
