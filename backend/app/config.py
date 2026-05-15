from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Check both backend/.env (for local dev when running uvicorn or pytest
        # from backend/) and the repo-root .env (used by docker compose). The
        # first existing file wins; values from later files don't override.
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    fireworks_api_key: str
    llm_model: str = "accounts/fireworks/models/glm-5p1"
    llm_base_url: str = "https://api.fireworks.ai/inference/v1"
    max_transcript_chars: int = 50000
    llm_timeout_seconds: int = 180
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value
