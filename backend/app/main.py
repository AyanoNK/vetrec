from fastapi import FastAPI

from app.api.timeline import (
    router as timeline_router,
    get_extractor as _api_get_extractor,
)
from app.config import Settings
from app.services.extractor import TimelineExtractor


def _build_extractor() -> TimelineExtractor:
    return TimelineExtractor(settings=Settings())


app = FastAPI(title="Case Timeline API")
app.dependency_overrides[_api_get_extractor] = _build_extractor

# Re-export the dependency symbol so tests can override it under the same name.
get_extractor = _api_get_extractor

app.include_router(timeline_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
