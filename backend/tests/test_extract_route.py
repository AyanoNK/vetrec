from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.errors import (
    EmptyTranscriptError,
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
    NotClinicalTranscriptError,
    TranscriptTooLongError,
)
from app.main import app, get_extractor
from app.services.extractor import TimelineExtractor


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "fk-test")
    return TestClient(app)


def _override_extractor(mock_extract):
    fake = TimelineExtractor(settings=Settings(_env_file=None))
    fake.extract = mock_extract  # type: ignore[assignment]
    app.dependency_overrides[get_extractor] = lambda: fake
    return fake


def teardown_function():
    app.dependency_overrides.clear()


def test_extract_returns_events(client):
    from baml_client.types import (
        DecisionStatus,
        DiagnosticEvent,
        HistoryEvent,
        Timeline,
    )

    timeline = Timeline(
        events=[
            HistoryEvent(
                type="history",
                order=0,
                title="Vomiting two days",
                description="Owner reports three episodes.",
            ),
            DiagnosticEvent(
                type="diagnostic",
                order=1,
                title="CBC ordered",
                description="Bloodwork sent out.",
                test_name="CBC",
                decision=DecisionStatus.Approved,
            ),
        ]
    )
    _override_extractor(AsyncMock(return_value=timeline))

    response = client.post(
        "/extract", json={"transcript": "Charlie presented for vomiting."}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == 2
    assert body["events"][0]["type"] == "history"
    assert body["events"][1]["type"] == "diagnostic"


def test_extract_rejects_empty(client):
    _override_extractor(AsyncMock(side_effect=EmptyTranscriptError("empty")))
    response = client.post("/extract", json={"transcript": ""})
    assert response.status_code == 422
    assert response.json()["error"] == "transcript_empty"


def test_extract_rejects_too_long(client):
    _override_extractor(
        AsyncMock(side_effect=TranscriptTooLongError(length=100, max_length=10))
    )
    response = client.post("/extract", json={"transcript": "x"})
    assert response.status_code == 422
    assert response.json()["error"] == "transcript_too_long"


def test_extract_handles_validation_failure(client):
    _override_extractor(AsyncMock(side_effect=ExtractionFailedError("bad json")))
    response = client.post("/extract", json={"transcript": "x"})
    assert response.status_code == 500
    assert response.json()["error"] == "extraction_failed"


def test_extract_handles_llm_unavailable(client):
    _override_extractor(AsyncMock(side_effect=LLMUnavailableError("503")))
    response = client.post("/extract", json={"transcript": "x"})
    assert response.status_code == 502
    assert response.json()["error"] == "llm_unavailable"


def test_extract_handles_timeout(client):
    _override_extractor(AsyncMock(side_effect=LLMTimeoutError("timeout")))
    response = client.post("/extract", json={"transcript": "x"})
    assert response.status_code == 504
    assert response.json()["error"] == "llm_timeout"


def test_extract_rejects_non_clinical(client):
    _override_extractor(
        AsyncMock(side_effect=NotClinicalTranscriptError(reason="looks like a recipe"))
    )
    response = client.post("/extract", json={"transcript": "x"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "not_clinical_transcript"
    assert body["reason"] == "looks like a recipe"


def test_rate_limit_headers_present(client):
    """Verify slowapi middleware is wired by checking standard rate-limit headers."""
    from baml_client.types import Timeline

    _override_extractor(AsyncMock(return_value=Timeline(events=[])))
    response = client.post("/extract", json={"transcript": "test content"})
    lower_headers = {h.lower() for h in response.headers}
    assert "x-ratelimit-limit" in lower_headers
    assert "x-ratelimit-remaining" in lower_headers


def test_healthz_exempt_from_rate_limit(client):
    """Verify /healthz is exempt from rate limiting (no rate-limit headers)."""
    response = client.get("/healthz")
    assert response.status_code == 200
    lower_headers = {h.lower() for h in response.headers}
    assert "x-ratelimit-limit" not in lower_headers


def test_rate_limit_returns_429_when_exceeded(monkeypatch):
    """Set RATE_LIMIT_PER_MINUTE=1, reload the app module, fire 2 requests."""
    import importlib

    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("FIREWORKS_API_KEY", "fk-test")

    import app.main as main_module

    importlib.reload(main_module)

    from app.main import _limiter, app as fresh_app
    from app.main import get_extractor as fresh_get_extractor

    _limiter.reset()

    from baml_client.types import Timeline

    fake = TimelineExtractor(settings=Settings(_env_file=None))
    fake.extract = AsyncMock(return_value=Timeline(events=[]))  # type: ignore[assignment]
    fresh_app.dependency_overrides[fresh_get_extractor] = lambda: fake

    from fastapi.testclient import TestClient

    fresh_client = TestClient(fresh_app)
    try:
        first = fresh_client.post("/extract", json={"transcript": "hello world"})
        assert first.status_code == 200
        second = fresh_client.post("/extract", json={"transcript": "hello world"})
        assert second.status_code == 429
        assert second.json()["error"] == "rate_limited"
    finally:
        _limiter.reset()
        fresh_app.dependency_overrides.clear()
        # Reload again to restore original settings so other tests aren't affected
        importlib.reload(main_module)
