from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # LLM Provider — "anthropic" or "openai"
    llm_provider: str = "anthropic"

    # Paths
    cases_path: str = "data/cases.json"
    chunks_path: str = "data/chunks.json"
    faiss_index_path: str = "data/faiss.index"

    # RAG Settings
    rag_top_k: int = 5
    embedding_model: str = "all-MiniLM-L6-v2"

    # LLM Settings
    llm_model: str = ""  # leave empty to use provider default
    llm_max_tokens: int = 1024

    # Session Settings
    default_resource_budget: int = 100
    session_timeout_minutes: int = 60

    # Server
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()