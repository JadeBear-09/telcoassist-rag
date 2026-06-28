from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TelcoAssist"
    app_env: str = "local"
    app_api_key: str | None = None
    auth_enabled: bool = False
    public_ask_enabled: bool = False
    rate_limit_per_minute: int = 120
    auto_ingest_on_startup: bool = False
    log_level: str = "INFO"
    max_upload_mb: int = 512
    max_upload_files: int = 10_000
    ingest_api_enabled: bool = True

    data_dir: Path = Field(default=Path("data"))
    raw_docs_dir: Path = Field(default=Path("data/raw"))
    processed_dir: Path = Field(default=Path("data/processed"))

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "telco_documents"
    use_qdrant: bool = False

    embedding_provider: str = "hashing"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"

    confidence_threshold: float = 0.38
    default_top_k: int = 6
    candidate_k: int = 50

    guardrails_enabled: bool = True
    max_question_chars: int = 4000
    max_context_chars: int = 12000
    max_answer_chars: int = 6000
    allow_user_openai_api_key: bool = True
    allow_user_gemini_api_key: bool = True

    @property
    def api_key_required(self) -> bool:
        return self.auth_enabled or bool(self.app_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
