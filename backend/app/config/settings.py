"""
Central configuration. All values are read from environment variables so the
evaluator can change behavior (including the LLM provider) without touching
code. See .env.example at the repo root for the full list with descriptions.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_env: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lenny_assistant"

    # --- LLM provider toggle ---
    # "anthropic" (cloud) or "ollama" (local). This is the single switch that
    # changes which model answers requests, with no code change required.
    llm_provider: Literal["anthropic", "ollama"] = "ollama"

    # Anthropic (cloud)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # Ollama (local) — mandatory path for the submitted demo
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: int = 120

    # Shared LLM behavior
    llm_max_tokens: int = 500
    llm_temperature: float = 0.3
    llm_request_timeout_seconds: int = 60

    # --- Retrieval / knowledge base ---
    transcripts_dir: str = "/app/data/transcripts"
    embedding_provider: Literal["anthropic", "local"] = "local"
    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 75
    retrieval_top_k: int = 6
    retrieval_min_score: float = 0.20  # below this, treat as "no relevant context"

    # --- Artifact rendering / security ---
    artifact_max_html_bytes: int = 200_000

    # --- CORS ---
    cors_allow_origins: str = "http://localhost:5173,http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
