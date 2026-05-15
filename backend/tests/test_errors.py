from app.core.errors import (
    EmptyTranscriptError,
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
    TimelineError,
    TranscriptTooLongError,
)


def test_transcript_too_long_carries_lengths():
    err = TranscriptTooLongError(length=100, max_length=50)
    assert err.length == 100
    assert err.max_length == 50


def test_all_domain_errors_share_base():
    for cls in (
        EmptyTranscriptError,
        TranscriptTooLongError,
        ExtractionFailedError,
        LLMUnavailableError,
        LLMTimeoutError,
    ):
        assert issubclass(cls, TimelineError)
