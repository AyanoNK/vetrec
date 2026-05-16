class TimelineError(Exception):
    """Base exception for the timeline domain."""


class EmptyTranscriptError(TimelineError):
    """Transcript is empty or whitespace only."""


class TranscriptTooLongError(TimelineError):
    """Transcript exceeds the configured maximum length."""

    def __init__(self, length: int, max_length: int) -> None:
        super().__init__(f"transcript {length} chars exceeds limit {max_length}")
        self.length = length
        self.max_length = max_length


class ExtractionFailedError(TimelineError):
    """LLM output failed BAML validation."""


class LLMUnavailableError(TimelineError):
    """LLM provider returned a transport or HTTP error."""


class LLMTimeoutError(TimelineError):
    """LLM call exceeded the configured timeout."""


class NotClinicalTranscriptError(TimelineError):
    """Transcript was classified as non-clinical and rejected before extraction."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"transcript classified as non-clinical: {reason}")
        self.reason = reason
