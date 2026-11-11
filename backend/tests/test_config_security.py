"""Production configuration must fail closed for browser security settings."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_insecure_cookie_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://pramana.example.gov.in")

    with pytest.raises(ValidationError, match="COOKIE_SECURE=true"):
        Settings(_env_file=None)


def test_production_rejects_wildcard_cors(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")

    with pytest.raises(ValidationError, match="Wildcard ALLOWED_ORIGINS"):
        Settings(_env_file=None)


def test_production_accepts_secure_cookie_and_explicit_https_origin(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://pramana.example.gov.in")

    settings = Settings(_env_file=None)
    assert settings.is_production is True
    assert settings.cookie_secure is True
    assert settings.origins == ["https://pramana.example.gov.in"]
