import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "fk-test")
    settings = Settings(_env_file=None)
    assert settings.fireworks_api_key == "fk-test"
    assert settings.llm_model == "accounts/fireworks/models/glm-5p1"
    assert settings.llm_base_url == "https://api.fireworks.ai/inference/v1"
    assert settings.max_transcript_chars == 50000
    assert settings.llm_timeout_seconds == 180


def test_settings_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_parses_cors_origins(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "fk-test")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost")
    settings = Settings(_env_file=None)
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost"]
