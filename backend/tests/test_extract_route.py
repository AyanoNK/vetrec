from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.errors import (
    EmptyTranscriptError,
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
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
