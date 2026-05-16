from app.core.errors import (
    EmptyTranscriptError,
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
    NotClinicalTranscriptError,
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
        NotClinicalTranscriptError,
    ):
        assert issubclass(cls, TimelineError)


def test_not_clinical_carries_reason():
    err = NotClinicalTranscriptError(reason="looks like a recipe")
    assert err.reason == "looks like a recipe"
