from app.config import Settings
from app.core.errors import EmptyTranscriptError, TranscriptTooLongError


class TimelineExtractor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def extract(self, transcript: str):
        self._validate(transcript)
        # BAML integration added in Task 11.
        raise NotImplementedError("BAML integration not yet wired")

    def _validate(self, transcript: str) -> None:
        if not transcript.strip():
            raise EmptyTranscriptError("transcript is empty")
        if len(transcript) > self.settings.max_transcript_chars:
            raise TranscriptTooLongError(
                length=len(transcript),
                max_length=self.settings.max_transcript_chars,
            )
