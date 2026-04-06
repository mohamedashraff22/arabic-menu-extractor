"""
Application settings loaded from environment variables.
Uses pydantic-settings for validation and .env file support.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Menu Extractor application."""

    model_config = SettingsConfigDict(
        env_file="src/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Kaggle OCR ───────────────────────────────────────────────
    KAGGLE_OCR_URL: str

    # ── OpenAI ───────────────────────────────────────────────────
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str
    OPENAI_CHAT_MODEL: str

    # ── Qdrant ───────────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "menu_items"

    # ── PostgreSQL ───────────────────────────────────────────────
    DATABASE_URL: str

    # ── Session TTL ──────────────────────────────────────────────
    SESSION_TTL_HOURS: int = 24
    SESSION_CLEANUP_INTERVAL_MINUTES: int = 60


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
