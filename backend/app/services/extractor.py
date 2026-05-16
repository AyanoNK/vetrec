import asyncio

from baml_client.async_client import b
from baml_client.types import Timeline
from baml_py.errors import (
    BamlClientFinishReasonError,
    BamlClientHttpError,
    BamlValidationError,
)

from app.config import Settings
from app.core.errors import (
    EmptyTranscriptError,
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
    NotClinicalTranscriptError,
    TranscriptTooLongError,
)


class TimelineExtractor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def extract(self, transcript: str) -> Timeline:
        self._validate(transcript)
        await self._classify(transcript)
        return await self._extract_events(transcript)

    async def _classify(self, transcript: str) -> None:
        try:
            result = await asyncio.wait_for(
                b.ClassifyTranscript(transcript=transcript),
                timeout=self.settings.llm_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError("classifier call timed out") from exc
        except BamlClientFinishReasonError as exc:
            raise ExtractionFailedError(f"classifier stopped early: {exc}") from exc
        except BamlValidationError as exc:
            raise ExtractionFailedError(
                f"classifier output failed validation: {exc}"
            ) from exc
        except BamlClientHttpError as exc:
            raise LLMUnavailableError(f"classifier provider error: {exc}") from exc

        if not result.is_clinical_transcript:
            raise NotClinicalTranscriptError(reason=result.reason)

    async def _extract_events(self, transcript: str) -> Timeline:
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
