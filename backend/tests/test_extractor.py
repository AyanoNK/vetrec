import pytest

from app.config import Settings
from app.core.errors import EmptyTranscriptError, TranscriptTooLongError
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
