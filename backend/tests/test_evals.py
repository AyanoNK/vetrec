"""Eval suite: runs the real LLM against labeled fixtures and asserts on
structural facts. Gated by the `eval` pytest marker (default-deselected). Run
with `uv run pytest -m eval` after setting a real FIREWORKS_API_KEY."""

import json
from pathlib import Path

import pytest

from app.config import Settings
from app.services.extractor import TimelineExtractor
from evals.assertions import (
    assert_diagnostic_present,
    assert_min_event_count,
    assert_recommendation_categories,
    assert_required_event_types,
    assert_treatment_present,
    assert_vitals_match,
)


FIXTURES_DIR = Path(__file__).parent.parent / "evals" / "fixtures"


def _load_fixtures() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(FIXTURES_DIR.glob("*.json"))]


def _ids(fixtures: list[dict]) -> list[str]:
    return [f["name"] for f in fixtures]


FIXTURES = _load_fixtures()


@pytest.mark.eval
@pytest.mark.parametrize("fixture", FIXTURES, ids=_ids(FIXTURES))
async def test_extraction_matches_expected(fixture):
    settings = Settings()
    extractor = TimelineExtractor(settings=settings)
    timeline = await extractor.extract(fixture["transcript"])

    expected = fixture["expected"]

    if "min_event_count" in expected:
        assert_min_event_count(timeline, expected["min_event_count"])

    if "required_event_types" in expected:
        assert_required_event_types(timeline, expected["required_event_types"])

    if "vitals" in expected:
        assert_vitals_match(timeline, expected["vitals"])

    for treatment in expected.get("treatments", []):
        assert_treatment_present(timeline, **treatment)

    for diagnostic in expected.get("diagnostics", []):
        assert_diagnostic_present(timeline, **diagnostic)

    if "recommendation_categories" in expected:
        assert_recommendation_categories(timeline, expected["recommendation_categories"])
