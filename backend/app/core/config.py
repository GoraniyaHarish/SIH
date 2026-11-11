"""Application configuration. Every secret comes from the environment."""
from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- application ---
    app_name: str = "PRAMANA"
    env: str = Field(default="development", validation_alias="APP_ENV")
    api_prefix: str = "/api"
    log_level: str = "INFO"

    # --- database ---
    database_url: str = "postgresql+psycopg://pramana:pramana_local_dev@127.0.0.1:5432/pramana"
    db_pool_size: int = 5
    db_echo: bool = False

    # --- auth ---
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    jwt_issuer: str = "pramana.local"
    password_min_length: int = 10
    login_max_attempts: int = 5
    login_window_seconds: int = 900
    lockout_threshold: int = 10
    lockout_seconds: int = 900
    cookie_secure: bool = False

    # --- cors ---
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    # --- uploads ---
    upload_dir: Path = Path("storage/uploads")
    max_upload_bytes: int = 20 * 1024 * 1024
    allowed_mime: str = "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"

    # --- redis (optional; rate limiting falls back to in-process) ---
    redis_url: str = "redis://127.0.0.1:6379/0"

    # --- AI provider (provider-neutral, OpenAI-compatible) ---
    ai_provider: str = "openai-compatible"
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_chat_model: str = "gpt-5-mini"
    ai_embedding_model: str = "text-embedding-3-small"
    ai_embedding_dim: int = 1536
    ai_timeout_seconds: float = 60.0
    ai_max_retries: int = 2
    ai_requests_per_minute: int = 120
    # Document and query text are never sent to an external AI provider unless explicitly enabled.
    ai_send_documents_externally: bool = False

    # --- RAG ---
    rag_min_similarity: float = 0.20
    rag_top_k: int = 6
    chunk_chars: int = 900
    chunk_overlap: int = 120

    # --- integration adapters (no default credentials ever) ---
    igot_base_url: str = ""
    igot_api_token: str = ""
    nssta_base_url: str = ""
    nssta_api_token: str = ""
    integration_timeout_seconds: float = 8.0

    # --- worker ---
    process_inline_worker: bool = True
    worker_poll_seconds: float = 1.5

    @field_validator("upload_dir")
    @classmethod
    def _mkdir(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v

    @model_validator(mode="after")
    def _validate_production_security(self) -> "Settings":
        if self.is_production and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE=true is required when APP_ENV=production")
        if self.is_production and "*" in self.origins:
            raise ValueError("Wildcard ALLOWED_ORIGINS is not permitted in production")
        return self

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def mime_allowlist(self) -> set[str]:
        return {m.strip() for m in self.allowed_mime.split(",") if m.strip()}

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_base_url and self.ai_api_key)

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
