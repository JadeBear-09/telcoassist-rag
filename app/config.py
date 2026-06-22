from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "TelcoAssist"
    app_env: str = "local"

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

    confidence_threshold: float = 0.38
    default_top_k: int = 6
    candidate_k: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
