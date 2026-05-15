import asyncio

from baml_client.async_client import b
from baml_client.types import Timeline
from baml_py.errors import BamlClientFinishReasonError, BamlClientHttpError, BamlValidationError

from app.config import Settings
from app.core.errors import (
    EmptyTranscriptError,
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
    TranscriptTooLongError,
)


class TimelineExtractor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def extract(self, transcript: str) -> Timeline:
        self._validate(transcript)
        try:
            result = await asyncio.wait_for(
                b.ExtractTimeline(transcript=transcript),
                timeout=self.settings.llm_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError("llm call timed out") from exc
        except BamlClientFinishReasonError as exc:
            raise ExtractionFailedError(f"llm stopped early: {exc}") from exc
        except BamlValidationError as exc:
            raise ExtractionFailedError(
                f"llm output failed validation: {exc}"
            ) from exc
        except BamlClientHttpError as exc:
            raise LLMUnavailableError(f"llm provider error: {exc}") from exc

        result.events.sort(key=lambda event: event.order)
        return result

    def _validate(self, transcript: str) -> None:
        if not transcript.strip():
            raise EmptyTranscriptError("transcript is empty")
        if len(transcript) > self.settings.max_transcript_chars:
            raise TranscriptTooLongError(
                length=len(transcript),
                max_length=self.settings.max_transcript_chars,
            )
