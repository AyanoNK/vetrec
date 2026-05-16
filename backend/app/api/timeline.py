from fastapi import APIRouter, Depends, Request

from app.schemas.timeline import ExtractRequest, ExtractResponse
from app.services.extractor import TimelineExtractor

router = APIRouter()


def get_extractor() -> TimelineExtractor:
    # Overridden in main.py via app.dependency_overrides at app startup.
    raise NotImplementedError("get_extractor must be overridden by app setup")


@router.post("/extract", response_model=ExtractResponse)
async def extract(
    request: Request,
    payload: ExtractRequest,
    extractor: TimelineExtractor = Depends(get_extractor),
) -> ExtractResponse:
    return await extractor.extract(payload.transcript)
