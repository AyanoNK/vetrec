"""Assertion helpers for the evals harness. Each function takes a BAML Timeline
plus the relevant slice of the fixture's `expected` block and raises AssertionError
on mismatch with a message clear enough to debug without re-reading the fixture."""

from baml_client.types import Timeline


def assert_min_event_count(timeline: Timeline, minimum: int) -> None:
    actual = len(timeline.events)
    assert actual >= minimum, (
        f"expected at least {minimum} events, got {actual}"
    )


def assert_required_event_types(timeline: Timeline, types: list[str]) -> None:
    actual_types = {event.type for event in timeline.events}
    missing = [t for t in types if t not in actual_types]
    assert not missing, (
        f"missing required event types: {missing}. got: {sorted(actual_types)}"
    )


def assert_vitals_match(timeline: Timeline, expected: dict[str, float]) -> None:
    vitals = [e for e in timeline.events if e.type == "vitals"]
    assert vitals, "no vitals event extracted"

    # Merge vitals across all vitals events (in case the LLM split them).
    merged: dict[str, float | None] = {}
    for event in vitals:
        for field in (
            "temperature_f",
            "heart_rate_bpm",
            "respiratory_rate",
            "weight_kg",
            "capillary_refill_seconds",
        ):
            value = getattr(event, field, None)
            if value is not None and merged.get(field) is None:
                merged[field] = value

    for field, expected_value in expected.items():
        actual = merged.get(field)
        assert actual == expected_value, (
            f"vitals.{field}: expected {expected_value}, got {actual}"
        )


def assert_treatment_present(
    timeline: Timeline,
    name_contains: str,
    decision: str | None = None,
    progress: str | None = None,
) -> None:
    needle = name_contains.lower()
    matches = [
        e for e in timeline.events
        if e.type == "treatment" and needle in (e.name or "").lower()
    ]
    assert matches, (
        f"no treatment event with name containing '{name_contains}'"
    )
    if decision is not None:
        decisions = [str(m.decision) for m in matches]
        assert any(decision in d for d in decisions), (
            f"treatment '{name_contains}': expected decision {decision}, got {decisions}"
        )
    if progress is not None:
        progresses = [str(m.progress) for m in matches]
        assert any(progress in p for p in progresses if p), (
            f"treatment '{name_contains}': expected progress {progress}, got {progresses}"
        )


def assert_diagnostic_present(
    timeline: Timeline,
    test_name_contains: str,
    decision: str | None = None,
) -> None:
    needle = test_name_contains.lower()
    matches = [
        e for e in timeline.events
        if e.type == "diagnostic" and needle in (e.test_name or "").lower()
    ]
    assert matches, (
        f"no diagnostic event with test_name containing '{test_name_contains}'"
    )
    if decision is not None:
        decisions = [str(m.decision) for m in matches]
        assert any(decision in d for d in decisions), (
            f"diagnostic '{test_name_contains}': expected decision {decision}, got {decisions}"
        )


def assert_recommendation_categories(
    timeline: Timeline,
    expected_categories: list[str],
) -> None:
    actual = {
        str(e.category) for e in timeline.events if e.type == "recommendation"
    }
    missing = [c for c in expected_categories if not any(c in a for a in actual)]
    assert not missing, (
        f"missing recommendation categories: {missing}. got: {sorted(actual)}"
    )
