import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from baml_client.types import (
    DecisionStatus,
    DiagnosticEvent,
    HistoryEvent,
    Timeline,
)

from app.config import Settings
from app.core.errors import (
    EmptyTranscriptError,
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
    TranscriptTooLongError,
)
from app.services.extractor import TimelineExtractor


def make_settings(**overrides) -> Settings:
    base = {"fireworks_api_key": "fk-test", "max_transcript_chars": 100}
    base.update(overrides)
    return Settings(_env_file=None, **base)


async def test_extract_rejects_empty_transcript():
    extractor = TimelineExtractor(settings=make_settings())
    with pytest.raises(EmptyTranscriptError):
        await extractor.extract("")


async def test_extract_rejects_whitespace_only():
    extractor = TimelineExtractor(settings=make_settings())
    with pytest.raises(EmptyTranscriptError):
        await extractor.extract("   \n\t  ")


async def test_extract_rejects_too_long():
    extractor = TimelineExtractor(settings=make_settings(max_transcript_chars=10))
    with pytest.raises(TranscriptTooLongError) as excinfo:
        await extractor.extract("x" * 100)
    assert excinfo.value.length == 100
    assert excinfo.value.max_length == 10


def _make_timeline_unsorted() -> Timeline:
    return Timeline(
        events=[
            DiagnosticEvent(
                type="diagnostic",
                order=2,
                title="Recommended CBC",
                description="Ordered bloodwork.",
                test_name="CBC",
                decision=DecisionStatus.Approved,
            ),
            HistoryEvent(
                type="history",
                order=0,
                title="Presenting complaint",
                description="Vomiting two days.",
            ),
            HistoryEvent(
                type="history",
                order=1,
                title="Diet history",
                description="Eats kibble; no recent changes.",
            ),
        ]
    )


@patch("app.services.extractor.b")
async def test_extract_returns_events_sorted_by_order(mock_b):
    mock_b.ExtractTimeline = AsyncMock(return_value=_make_timeline_unsorted())
    extractor = TimelineExtractor(settings=make_settings())
    result = await extractor.extract("Charlie presented for vomiting.")
    assert [e.order for e in result.events] == [0, 1, 2]


@patch("app.services.extractor.b")
async def test_extract_maps_timeout(mock_b):
    async def slow(**_):
        await asyncio.sleep(10)

    mock_b.ExtractTimeline = AsyncMock(side_effect=slow)
    extractor = TimelineExtractor(
        settings=make_settings(llm_timeout_seconds=1)
    )
    with pytest.raises(LLMTimeoutError):
        await extractor.extract("any transcript")


@patch("app.services.extractor.b")
async def test_extract_maps_validation_error(mock_b):
    from baml_py.errors import BamlValidationError

    mock_b.ExtractTimeline = AsyncMock(
        side_effect=BamlValidationError(
            prompt="prompt",
            message="bad output",
            raw_output="raw",
            detailed_message="details",
        )
    )
    extractor = TimelineExtractor(settings=make_settings())
    with pytest.raises(ExtractionFailedError):
        await extractor.extract("any transcript")


@patch("app.services.extractor.b")
async def test_extract_maps_http_error(mock_b):
    from baml_py.errors import BamlClientHttpError

    mock_b.ExtractTimeline = AsyncMock(
        side_effect=BamlClientHttpError(
            client_name="fireworks",
            message="upstream 503",
            status_code=503,
            detailed_message="Service Unavailable",
        )
    )
    extractor = TimelineExtractor(settings=make_settings())
    with pytest.raises(LLMUnavailableError):
        await extractor.extract("any transcript")


@patch("app.services.extractor.b")
async def test_extract_maps_finish_reason_error(mock_b):
    from baml_py.errors import BamlClientFinishReasonError

    mock_b.ExtractTimeline = AsyncMock(
        side_effect=BamlClientFinishReasonError(
            prompt="prompt",
            message="model stopped due to length",
            raw_output="",
            finish_reason="length",
            detailed_message="output truncated",
        )
    )
    extractor = TimelineExtractor(settings=make_settings())
    with pytest.raises(ExtractionFailedError):
        await extractor.extract("any transcript")
