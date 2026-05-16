from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware
from slowapi.util import get_remote_address

from app.api.timeline import (
    get_extractor as _api_get_extractor,
    router as timeline_router,
)
from app.config import Settings
from app.core.errors import (
    EmptyTranscriptError,
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
    NotClinicalTranscriptError,
    TimelineError,
    TranscriptTooLongError,
)
from app.services.extractor import TimelineExtractor


_settings = Settings()

_limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{_settings.rate_limit_per_minute}/minute"],
    headers_enabled=True,
)


def _build_extractor() -> TimelineExtractor:
    return TimelineExtractor(settings=_settings)


app = FastAPI(title="Case Timeline API")
app.state.limiter = _limiter
app.add_middleware(SlowAPIASGIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.dependency_overrides[_api_get_extractor] = _build_extractor
get_extractor = _api_get_extractor

app.include_router(timeline_router)


@app.exception_handler(RateLimitExceeded)
async def _rate_limited(_: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limited",
            "detail": "Too many requests. Try again in a moment.",
        },
    )


@app.exception_handler(EmptyTranscriptError)
async def _empty(_: Request, exc: EmptyTranscriptError):
    return JSONResponse(
        status_code=422,
        content={"error": "transcript_empty", "detail": str(exc)},
    )


@app.exception_handler(TranscriptTooLongError)
async def _too_long(_: Request, exc: TranscriptTooLongError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "transcript_too_long",
            "detail": str(exc),
            "length": exc.length,
            "max_length": exc.max_length,
        },
    )


@app.exception_handler(NotClinicalTranscriptError)
async def _not_clinical(_: Request, exc: NotClinicalTranscriptError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "not_clinical_transcript",
            "detail": str(exc),
            "reason": exc.reason,
        },
    )


@app.exception_handler(ExtractionFailedError)
async def _extraction_failed(_: Request, exc: ExtractionFailedError):
    return JSONResponse(
        status_code=500,
        content={"error": "extraction_failed", "detail": str(exc)},
    )


@app.exception_handler(LLMUnavailableError)
async def _llm_unavailable(_: Request, exc: LLMUnavailableError):
    return JSONResponse(
        status_code=502,
        content={"error": "llm_unavailable", "detail": str(exc)},
    )


@app.exception_handler(LLMTimeoutError)
async def _llm_timeout(_: Request, exc: LLMTimeoutError):
    return JSONResponse(
        status_code=504,
        content={"error": "llm_timeout", "detail": str(exc)},
    )


@app.exception_handler(TimelineError)
async def _timeline_fallback(_: Request, exc: TimelineError):
    return JSONResponse(status_code=500, content={"error": "internal"})


@app.get("/healthz")
@_limiter.exempt
def healthz() -> dict[str, str]:
    return {"status": "ok"}
