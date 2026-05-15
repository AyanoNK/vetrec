# Case Timeline Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stateless FastAPI backend that extracts a structured case timeline from a veterinary medical transcript using BAML + GLM 5.1 on Fireworks.

**Architecture:** Layered FastAPI (api routers, service layer, schemas, errors) wrapping a single BAML function. Stateless `POST /extract` returns a sorted list of typed discriminated-union events. `uv` for Python tooling. Docker Compose with one `api` service (frontend deferred to a separate plan).

**Tech Stack:** Python 3.12, FastAPI, uv, BAML (`baml-py`), GLM 5.1 via Fireworks (OpenAI-compatible), pytest + pytest-asyncio, Docker Compose.

**Scope:** Backend only. The frontend gets its own spec and plan in a follow-up iteration.

**Reference spec:** `docs/superpowers/specs/2026-05-14-case-timeline-design.md`

**Project conventions** (`CLAUDE.md`): commit messages start lowercase, present-tense imperative, concise, granular. One logical change per commit. No AI attribution. No `Co-Authored-By` trailers.

**Testing strategy:**
- Python unit/integration tests **always run** — they mock BAML entirely.
- BAML `test` blocks run via `uv run baml-cli test` only when `FIREWORKS_API_KEY` is set; they hit the real LLM.

---

## Task 1: scaffold backend project with uv

**Files:**
- Create: `backend/.python-version`
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/app
printf "3.12\n" > backend/.python-version
touch backend/app/__init__.py
```

- [ ] **Step 2: Write `backend/pyproject.toml`**

```toml
[project]
name = "vetrec-backend"
version = "0.1.0"
description = "Case timeline extraction backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "baml-py>=0.70",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 3: Write minimal `backend/app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="Case Timeline API")
```

- [ ] **Step 4: Run `uv sync` to install dependencies**

```bash
cd backend && uv sync
```

Expected: creates `backend/uv.lock` and `backend/.venv/`. Verify with `ls backend/uv.lock`.

- [ ] **Step 5: Verify the app starts**

```bash
cd backend && uv run uvicorn app.main:app --port 8000 &
sleep 2
curl -sf http://localhost:8000/openapi.json | head -c 80
kill %1
```

Expected: prints the first ~80 chars of the OpenAPI JSON (something like `{"openapi":"3.1.0","info":{"title":"Case Timeline API"...`).

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "scaffold backend with uv and fastapi"
```

---

## Task 2: add /healthz endpoint with test

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_health.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_health.py`:
```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz_returns_ok():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Create `backend/tests/__init__.py`** (empty file)

```bash
touch backend/tests/__init__.py
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_health.py -v
```

Expected: FAIL with `404 Not Found`.

- [ ] **Step 4: Add the `/healthz` route**

`backend/app/main.py`:
```python
from fastapi import FastAPI

app = FastAPI(title="Case Timeline API")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/__init__.py backend/tests/test_health.py backend/app/main.py
git commit -m "add healthz endpoint"
```

---

## Task 3: add settings module with env-based config

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_config.py`:
```python
import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "fk-test")
    settings = Settings(_env_file=None)
    assert settings.fireworks_api_key == "fk-test"
    assert settings.llm_model == "accounts/fireworks/models/glm-5p1"
    assert settings.llm_base_url == "https://api.fireworks.ai/inference/v1"
    assert settings.max_transcript_chars == 50000
    assert settings.llm_timeout_seconds == 60


def test_settings_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_parses_cors_origins(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "fk-test")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost")
    settings = Settings(_env_file=None)
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'`.

- [ ] **Step 3: Implement `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    fireworks_api_key: str
    llm_model: str = "accounts/fireworks/models/glm-5p1"
    llm_base_url: str = "https://api.fireworks.ai/inference/v1"
    max_transcript_chars: int = 50000
    llm_timeout_seconds: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]

    @classmethod
    def _parse_csv(cls, raw: str) -> list[str]:
        return [item.strip() for item in raw.split(",") if item.strip()]

    def model_post_init(self, __context) -> None:
        if isinstance(self.cors_origins, str):
            object.__setattr__(
                self, "cors_origins", self._parse_csv(self.cors_origins)
            )
```

Note: pydantic-settings parses comma-separated env vars into `list[str]` natively via JSON or the field's parser. If `model_post_init` is awkward in your version, use `field_validator` instead — the test contract is what matters.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/test_config.py -v
```

Expected: PASS. If `test_settings_parses_cors_origins` fails on the list parse, switch to a `field_validator`:

```python
from pydantic import field_validator

# inside Settings:
@field_validator("cors_origins", mode="before")
@classmethod
def split_cors_origins(cls, v):
    if isinstance(v, str):
        return [item.strip() for item in v.split(",") if item.strip()]
    return v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "add settings module"
```

---

## Task 4: add BAML client definition

**Files:**
- Create: `backend/baml_src/clients.baml`

- [ ] **Step 1: Write `backend/baml_src/clients.baml`**

```
client<llm> GLM51 {
  provider openai-generic
  options {
    base_url env.LLM_BASE_URL
    api_key env.FIREWORKS_API_KEY
    model env.LLM_MODEL
    temperature 0.0
  }
}

retry_policy ProviderRetry {
  max_retries 2
  strategy {
    type exponential_backoff
    delay_ms 500
    multiplier 2
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add backend/baml_src/clients.baml
git commit -m "add baml client for fireworks glm 5.1"
```

---

## Task 5: add BAML schema (enums and event variants)

**Files:**
- Create: `backend/baml_src/timeline.baml`

- [ ] **Step 1: Write the schema portion of `backend/baml_src/timeline.baml`**

```
// Status for things the clinician proposes; the client accepts or refuses.
enum DecisionStatus {
  Approved
  Declined
  Pending
}

// Status for things with a temporal completion state.
enum ProgressStatus {
  Completed
  InProgress
  Pending
}

enum RecommendationCategory {
  Vaccine
  Medication
  Diet
  FollowUp
  Other
}

class HistoryEvent {
  type "history"
  order int @description("0-based position in the transcript")
  title string @description("Short label, under 80 chars")
  description string @description("1-2 sentence supporting detail")
}

class PhysicalExamEvent {
  type "physical_exam"
  order int
  title string
  description string
  findings_by_system (string | string[])? @description("Optional map of body system to finding")
}

class VitalsEvent {
  type "vitals"
  order int
  title string
  description string
  temperature_f float?
  heart_rate_bpm int?
  respiratory_rate int?
  weight_kg float?
  mucous_membranes string?
  capillary_refill_seconds float?
}

class DiagnosticEvent {
  type "diagnostic"
  order int
  title string
  description string
  test_name string
  indication string?
  decision DecisionStatus
  result string?
}

class TreatmentEvent {
  type "treatment"
  order int
  title string
  description string
  name string @description("Treatment or medication name")
  dose string?
  route string?
  decision DecisionStatus
  progress ProgressStatus?
}

class RecommendationEvent {
  type "recommendation"
  order int
  title string
  description string
  category RecommendationCategory
  specifics string?
}

class Timeline {
  events (
    HistoryEvent
    | PhysicalExamEvent
    | VitalsEvent
    | DiagnosticEvent
    | TreatmentEvent
    | RecommendationEvent
  )[]
}
```

Note on `findings_by_system`: BAML's map type support varies by version. If `map<string, string>` works in your BAML version, prefer that; if not, use `string?` (free-form) and revisit later. The plan uses a permissive union as a portable default. The executor should adapt to what their BAML version supports and update the spec if the field shape changes.

- [ ] **Step 2: Commit**

```bash
git add backend/baml_src/timeline.baml
git commit -m "add baml event schema"
```

---

## Task 6: add BAML ExtractTimeline function

**Files:**
- Modify: `backend/baml_src/timeline.baml`

- [ ] **Step 1: Append the function to `backend/baml_src/timeline.baml`**

```
function ExtractTimeline(transcript: string) -> Timeline {
  client GLM51
  prompt #"
    You are extracting a structured veterinary case timeline from a plain-text
    consultation transcript.

    Extract events of these six types, IN THE ORDER THEY APPEAR in the transcript:
    - history: presenting complaint and history of present illness
    - physical_exam: physical examination findings (excluding vital signs)
    - vitals: temperature, heart rate, respiratory rate, weight, mucous membranes,
      capillary refill — capture only what is explicitly stated
    - diagnostic: tests offered or run; capture whether they were approved or
      declined by the client
    - treatment: treatments offered or given; capture decision (approved/declined)
      and progress (completed/in_progress) when stated
    - recommendation: vaccines, medications, diet, follow-up plans

    Rules:
    - Use the `order` field to number events starting at 0 in transcript order.
    - Each event must have a concise `title` (under 80 chars) and a 1-2 sentence
      `description` drawn from the transcript. Do not invent details.
    - Only fill optional fields when the transcript explicitly states them.
    - If a value is uncertain or absent, omit the field rather than guessing.
    - Do not merge distinct events; do not duplicate the same event.

    {{ ctx.output_format }}

    Transcript:
    {{ transcript }}
  "#
}
```

- [ ] **Step 2: Commit**

```bash
git add backend/baml_src/timeline.baml
git commit -m "add extract timeline baml function"
```

---

## Task 7: generate baml_client and verify imports

**Files:**
- Create (generated): `backend/baml_client/` (committed)

- [ ] **Step 1: Generate the client**

```bash
cd backend && uv run baml-cli generate
```

Expected: `backend/baml_client/` directory is created with generated Python files (e.g. `__init__.py`, `async_client.py`, `types.py`).

- [ ] **Step 2: Verify generated types import**

```bash
cd backend && uv run python -c "from baml_client.types import Timeline, DecisionStatus; print('ok')"
```

Expected: prints `ok` with no errors.

- [ ] **Step 3: Verify the async client imports**

```bash
cd backend && uv run python -c "from baml_client.async_client import b; print(type(b).__name__)"
```

Expected: prints a class name (typically `BamlAsyncClient` or similar). If the import path differs in your BAML version, check `backend/baml_client/__init__.py` for the correct one and use it in subsequent tasks.

- [ ] **Step 4: Commit**

```bash
git add backend/baml_client/
git commit -m "generate baml client"
```

---

## Task 8: add three BAML test fixtures

**Files:**
- Modify: `backend/baml_src/timeline.baml`

- [ ] **Step 1: Append three `test` blocks to `backend/baml_src/timeline.baml`**

```
test routine_wellness {
  functions [ExtractTimeline]
  args {
    transcript #"
      Dr. Patel saw Bella, a 4-year-old female spayed Labrador retriever, today
      for her annual wellness exam. Owner reports normal appetite, energy, and
      bowel movements. No coughing or sneezing. Physical exam: bright, alert,
      responsive. BCS 5/9, mucous membranes pink and moist, capillary refill
      under 2 seconds. Temperature 101.4F. Heart rate 84 bpm, regular rhythm.
      Respiratory rate 24, lungs clear. Discussed annual vaccines; owner
      approved. Administered DA2PP and rabies boosters today. Recommended
      heartworm prevention monthly. Recheck in one year.
    "#
  }
}

test gi_workup_declined {
  functions [ExtractTimeline]
  args {
    transcript #"
      Charlie, 8-year-old neutered male shepherd mix, presented for vomiting
      two days. Owner reports three episodes of yellow vomit, decreased
      appetite. Physical exam shows mild dehydration, mucous membranes tacky,
      abdomen tense on palpation. Temperature 102.8F, heart rate 110, weight
      28.5 kg. Recommended CBC, chemistry panel, and abdominal radiographs to
      evaluate. Owner declined diagnostics today due to cost; agreed to
      symptomatic treatment. Started maropitant 1 mg/kg subq, given in clinic.
      Recommended bland diet for 48 hours. Recheck if vomiting persists or
      worsens.
    "#
  }
}

test emergency_in_progress {
  functions [ExtractTimeline]
  args {
    transcript #"
      Max, 6-year-old intact male boxer, brought in after being struck by a
      car 30 minutes ago. On presentation: tachycardic at 180 bpm, respiratory
      rate 60 with shallow breathing, mucous membranes pale, CRT 3 seconds,
      temperature 99.1F. Mentation dull. Triage exam reveals abrasions on
      right thoracic wall and right pelvic limb lameness. Placed IV catheter,
      started lactated ringers bolus 20 mL/kg, currently in progress.
      Recommended chest radiographs and abdominal FAST scan; owner approved.
      Considering opioid analgesia pending stabilization.
    "#
  }
}
```

- [ ] **Step 2: If `FIREWORKS_API_KEY` is set, run BAML tests**

```bash
cd backend && [ -n "$FIREWORKS_API_KEY" ] && uv run baml-cli test || echo "skipping: no api key"
```

Expected: if key present, each test runs and the function returns a parseable `Timeline`. If not, output says `skipping`.

- [ ] **Step 3: Commit**

```bash
git add backend/baml_src/timeline.baml
git commit -m "add baml test fixtures"
```

---

## Task 9: add domain error types

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/errors.py`
- Create: `backend/tests/test_errors.py`

- [ ] **Step 1: Create core package**

```bash
touch backend/app/core/__init__.py
```

- [ ] **Step 2: Write the failing test**

`backend/tests/test_errors.py`:
```python
from app.core.errors import (
    EmptyTranscriptError,
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
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
    ):
        assert issubclass(cls, TimelineError)
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_errors.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement `backend/app/core/errors.py`**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/test_errors.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/__init__.py backend/app/core/errors.py backend/tests/test_errors.py
git commit -m "add domain error types"
```

---

## Task 10: add TimelineExtractor service with input validation

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/extractor.py`
- Create: `backend/tests/test_extractor.py`

This task covers input validation only. BAML integration is added in Task 11.

- [ ] **Step 1: Create services package**

```bash
touch backend/app/services/__init__.py
```

- [ ] **Step 2: Write the failing test**

`backend/tests/test_extractor.py`:
```python
import pytest

from app.config import Settings
from app.core.errors import EmptyTranscriptError, TranscriptTooLongError
from app.services.extractor import TimelineExtractor


def make_settings(**overrides) -> Settings:
    base = {"fireworks_api_key": "fk-test", "max_transcript_chars": 100}
    base.update(overrides)
    return Settings(_env_file=None, **base)


async def test_extract_rejects_empty_transcript():
    extractor = TimelineExtractor(settings=make_settings())
    with pytest.raises(EmptyTranscriptError):
        await extractor.extract("")


async def test_extract_rejects_whitespace_only():
    extractor = TimelineExtractor(settings=make_settings())
    with pytest.raises(EmptyTranscriptError):
        await extractor.extract("   \n\t  ")


async def test_extract_rejects_too_long(monkeypatch):
    extractor = TimelineExtractor(settings=make_settings(max_transcript_chars=10))
    with pytest.raises(TranscriptTooLongError) as excinfo:
        await extractor.extract("x" * 100)
    assert excinfo.value.length == 100
    assert excinfo.value.max_length == 10
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_extractor.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.extractor'`.

- [ ] **Step 4: Implement `backend/app/services/extractor.py`** (validation only)

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/test_extractor.py -v
```

Expected: PASS (all three validation tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/extractor.py backend/tests/test_extractor.py
git commit -m "add transcript validation to extractor"
```

---

## Task 11: wire BAML into the extractor with error mapping

**Files:**
- Modify: `backend/app/services/extractor.py`
- Modify: `backend/tests/test_extractor.py`

- [ ] **Step 1: Add tests for the BAML integration**

Append to `backend/tests/test_extractor.py`:

```python
import asyncio
from unittest.mock import AsyncMock, patch

from baml_client.types import (
    DecisionStatus,
    DiagnosticEvent,
    HistoryEvent,
    Timeline,
)

from app.core.errors import (
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
)


def _make_timeline_unsorted() -> Timeline:
    return Timeline(
        events=[
            DiagnosticEvent(
                type="diagnostic",
                order=2,
                title="Recommended CBC",
                description="Ordered bloodwork.",
                test_name="CBC",
                decision=DecisionStatus.Approved,
            ),
            HistoryEvent(
                type="history",
                order=0,
                title="Presenting complaint",
                description="Vomiting two days.",
            ),
            HistoryEvent(
                type="history",
                order=1,
                title="Diet history",
                description="Eats kibble; no recent changes.",
            ),
        ]
    )


@patch("app.services.extractor.b")
async def test_extract_returns_events_sorted_by_order(mock_b):
    mock_b.ExtractTimeline = AsyncMock(return_value=_make_timeline_unsorted())
    extractor = TimelineExtractor(settings=make_settings())
    result = await extractor.extract("Charlie presented for vomiting.")
    assert [e.order for e in result.events] == [0, 1, 2]


@patch("app.services.extractor.b")
async def test_extract_maps_timeout(mock_b):
    async def slow(**_):
        await asyncio.sleep(10)

    mock_b.ExtractTimeline = AsyncMock(side_effect=slow)
    extractor = TimelineExtractor(
        settings=make_settings(llm_timeout_seconds=1)
    )
    with pytest.raises(LLMTimeoutError):
        await extractor.extract("any transcript")


@patch("app.services.extractor.b")
async def test_extract_maps_validation_error(mock_b):
    from baml_py.errors import BamlValidationError

    mock_b.ExtractTimeline = AsyncMock(
        side_effect=BamlValidationError("bad output", "raw", "Timeline")
    )
    extractor = TimelineExtractor(settings=make_settings())
    with pytest.raises(ExtractionFailedError):
        await extractor.extract("any transcript")


@patch("app.services.extractor.b")
async def test_extract_maps_http_error(mock_b):
    from baml_py.errors import BamlClientHttpError

    mock_b.ExtractTimeline = AsyncMock(
        side_effect=BamlClientHttpError("upstream 503", 503)
    )
    extractor = TimelineExtractor(settings=make_settings())
    with pytest.raises(LLMUnavailableError):
        await extractor.extract("any transcript")
```

Note on BAML error class signatures: the exact constructor parameters for `BamlValidationError` and `BamlClientHttpError` may differ between BAML versions. If the call signatures above don't match your installed version, adjust the test to use the correct constructor — the test contract is "BAML raises X → extractor raises Y", not the exact `__init__` shape.

- [ ] **Step 2: Run new tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_extractor.py -v
```

Expected: the new four tests FAIL (extractor still raises `NotImplementedError`).

- [ ] **Step 3: Implement the BAML integration in `backend/app/services/extractor.py`**

```python
import asyncio

from baml_client.async_client import b
from baml_client.types import Timeline
from baml_py.errors import BamlClientHttpError, BamlValidationError

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
```

If the BAML async client import path differs in your version (it could be `from baml_client import b` directly), use whichever path the Task 7 verification confirmed.

- [ ] **Step 4: Run all extractor tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_extractor.py -v
```

Expected: all seven tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/extractor.py backend/tests/test_extractor.py
git commit -m "wire baml into extractor with error mapping"
```

---

## Task 12: add /extract route with request/response schemas

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/timeline.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/timeline.py`
- Create: `backend/tests/test_extract_route.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create packages**

```bash
touch backend/app/api/__init__.py backend/app/schemas/__init__.py
```

- [ ] **Step 2: Write the failing tests**

`backend/tests/test_extract_route.py`:
```python
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.errors import (
    EmptyTranscriptError,
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
    TranscriptTooLongError,
)
from app.main import app, get_extractor
from app.services.extractor import TimelineExtractor


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "fk-test")
    return TestClient(app)


def _override_extractor(mock_extract):
    fake = TimelineExtractor(settings=Settings(_env_file=None))
    fake.extract = mock_extract  # type: ignore[assignment]
    app.dependency_overrides[get_extractor] = lambda: fake
    return fake


def teardown_function():
    app.dependency_overrides.clear()


def test_extract_returns_events(client):
    from baml_client.types import DecisionStatus, DiagnosticEvent, HistoryEvent, Timeline

    timeline = Timeline(
        events=[
            HistoryEvent(
                type="history",
                order=0,
                title="Vomiting two days",
                description="Owner reports three episodes.",
            ),
            DiagnosticEvent(
                type="diagnostic",
                order=1,
                title="CBC ordered",
                description="Bloodwork sent out.",
                test_name="CBC",
                decision=DecisionStatus.Approved,
            ),
        ]
    )
    _override_extractor(AsyncMock(return_value=timeline))

    response = client.post("/extract", json={"transcript": "Charlie presented for vomiting."})
    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == 2
    assert body["events"][0]["type"] == "history"
    assert body["events"][1]["type"] == "diagnostic"


def test_extract_rejects_empty(client):
    _override_extractor(AsyncMock(side_effect=EmptyTranscriptError("empty")))
    response = client.post("/extract", json={"transcript": ""})
    assert response.status_code == 422
    assert response.json()["error"] == "transcript_empty"


def test_extract_rejects_too_long(client):
    _override_extractor(
        AsyncMock(side_effect=TranscriptTooLongError(length=100, max_length=10))
    )
    response = client.post("/extract", json={"transcript": "x"})
    assert response.status_code == 422
    assert response.json()["error"] == "transcript_too_long"


def test_extract_handles_validation_failure(client):
    _override_extractor(AsyncMock(side_effect=ExtractionFailedError("bad json")))
    response = client.post("/extract", json={"transcript": "x"})
    assert response.status_code == 500
    assert response.json()["error"] == "extraction_failed"


def test_extract_handles_llm_unavailable(client):
    _override_extractor(AsyncMock(side_effect=LLMUnavailableError("503")))
    response = client.post("/extract", json={"transcript": "x"})
    assert response.status_code == 502
    assert response.json()["error"] == "llm_unavailable"


def test_extract_handles_timeout(client):
    _override_extractor(AsyncMock(side_effect=LLMTimeoutError("timeout")))
    response = client.post("/extract", json={"transcript": "x"})
    assert response.status_code == 504
    assert response.json()["error"] == "llm_timeout"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_extract_route.py -v
```

Expected: FAIL with `ImportError` on `get_extractor` or `404` on `/extract`.

- [ ] **Step 4: Implement API schemas**

`backend/app/schemas/timeline.py`:
```python
from pydantic import BaseModel, Field

from baml_client.types import Timeline as BamlTimeline


class ExtractRequest(BaseModel):
    transcript: str = Field(..., description="Plain-text consultation transcript")


# Response is the BAML Timeline directly. The discriminated-union types
# generated by BAML are Pydantic v2 models, so FastAPI serializes them
# natively. If your BAML version emits dataclasses instead, wrap with
# Pydantic adapters here.
ExtractResponse = BamlTimeline


class ErrorBody(BaseModel):
    error: str
    detail: str | None = None
```

- [ ] **Step 5: Implement the router**

`backend/app/api/timeline.py`:
```python
from fastapi import APIRouter, Depends

from app.schemas.timeline import ExtractRequest, ExtractResponse
from app.services.extractor import TimelineExtractor

router = APIRouter()


def get_extractor() -> TimelineExtractor:
    # Overridden in main.py via app.dependency_overrides / FastAPI DI.
    raise NotImplementedError("get_extractor must be overridden by app setup")


@router.post("/extract", response_model=ExtractResponse)
async def extract(
    payload: ExtractRequest,
    extractor: TimelineExtractor = Depends(get_extractor),
) -> ExtractResponse:
    return await extractor.extract(payload.transcript)
```

- [ ] **Step 6: Wire the router and DI in `backend/app/main.py`**

`backend/app/main.py`:
```python
from fastapi import FastAPI

from app.api.timeline import router as timeline_router, get_extractor as _api_get_extractor
from app.config import Settings
from app.services.extractor import TimelineExtractor


def _build_extractor() -> TimelineExtractor:
    return TimelineExtractor(settings=Settings())


app = FastAPI(title="Case Timeline API")
app.dependency_overrides[_api_get_extractor] = _build_extractor


# Re-export the dependency symbol so tests can override it via the same name.
get_extractor = _api_get_extractor

app.include_router(timeline_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 7: Run tests; some pass, error-mapping tests still fail**

```bash
cd backend && uv run pytest tests/test_extract_route.py -v
```

Expected: `test_extract_returns_events` PASSES. The four error-mapping tests still FAIL (no exception handlers yet).

- [ ] **Step 8: Commit (partial — handlers added next task)**

```bash
git add backend/app/api/ backend/app/schemas/ backend/app/main.py backend/tests/test_extract_route.py
git commit -m "add extract route and request schemas"
```

---

## Task 13: add exception handlers mapping domain errors to HTTP codes

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add exception handlers in `backend/app/main.py`**

Replace the contents of `backend/app/main.py` with:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.timeline import (
    router as timeline_router,
    get_extractor as _api_get_extractor,
)
from app.config import Settings
from app.core.errors import (
    EmptyTranscriptError,
    ExtractionFailedError,
    LLMTimeoutError,
    LLMUnavailableError,
    TimelineError,
    TranscriptTooLongError,
)
from app.services.extractor import TimelineExtractor


def _build_extractor() -> TimelineExtractor:
    return TimelineExtractor(settings=Settings())


app = FastAPI(title="Case Timeline API")
app.dependency_overrides[_api_get_extractor] = _build_extractor
get_extractor = _api_get_extractor

app.include_router(timeline_router)


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
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 2: Run all route tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_extract_route.py -v
```

Expected: all six tests PASS.

- [ ] **Step 3: Run the full test suite**

```bash
cd backend && uv run pytest -v
```

Expected: every test passes.

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "map domain errors to http status codes"
```

---

## Task 14: add CORS middleware

**Files:**
- Create: `backend/tests/conftest.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_health.py`

This task introduces a module-level `Settings()` call in `main.py` (CORS middleware needs the configured origin list at app construction time). That means any test module importing `app.main` requires the required env vars to be set **before the import line runs** — earlier than monkeypatch fixtures fire. A `conftest.py` at the tests/ root sets safe defaults before any test module loads.

- [ ] **Step 1: Create `backend/tests/conftest.py`**

```python
import os

# Set safe defaults before any test module imports app.main. Individual tests
# can still override via monkeypatch.setenv / monkeypatch.delenv as needed.
os.environ.setdefault("FIREWORKS_API_KEY", "fk-test")
os.environ.setdefault("LLM_MODEL", "accounts/fireworks/models/glm-5p1")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
```

- [ ] **Step 2: Add a CORS preflight test**

Append to `backend/tests/test_health.py`:

```python
def test_cors_allows_configured_origin():
    response = client.options(
        "/healthz",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
```

- [ ] **Step 3: Run to verify it fails**

```bash
cd backend && uv run pytest tests/test_health.py::test_cors_allows_configured_origin -v
```

Expected: FAIL — no `access-control-allow-origin` header (CORS middleware not yet added).

- [ ] **Step 4: Add CORS middleware to `backend/app/main.py`**

Insert after the `app = FastAPI(...)` line and before `app.dependency_overrides[...]`:

```python
from fastapi.middleware.cors import CORSMiddleware

_settings = Settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Note: this construction of `Settings()` at import time requires env vars to be present when the module loads. `conftest.py` from Step 1 covers tests; production loads from `.env`.

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd backend && uv run pytest tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 6: Run the full suite**

```bash
cd backend && uv run pytest -v
```

Expected: every test passes.

- [ ] **Step 7: Commit**

```bash
git add backend/tests/conftest.py backend/app/main.py backend/tests/test_health.py
git commit -m "enable cors for configured origins"
```

---

## Task 15: add backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

- [ ] **Step 1: Write `backend/.dockerignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
tests/
```

- [ ] **Step 2: Write `backend/Dockerfile`**

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install deps (cached when only source changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application and BAML client (already generated and committed)
COPY app ./app
COPY baml_src ./baml_src
COPY baml_client ./baml_client

RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Build the image**

```bash
cd backend && docker build -t vetrec-backend:dev .
```

Expected: build succeeds, image tagged `vetrec-backend:dev`.

- [ ] **Step 4: Run a smoke check**

```bash
docker run --rm -d --name vetrec-smoke -p 18000:8000 \
    -e FIREWORKS_API_KEY=placeholder \
    vetrec-backend:dev
sleep 3
curl -sf http://localhost:18000/healthz
docker stop vetrec-smoke
```

Expected: prints `{"status":"ok"}`.

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "add backend dockerfile"
```

---

## Task 16: add docker-compose and env example

**Files:**
- Create: `docker-compose.yml` (repo root)
- Create: `.env.example` (repo root)

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - FIREWORKS_API_KEY=${FIREWORKS_API_KEY}
      - LLM_MODEL=${LLM_MODEL:-accounts/fireworks/models/glm-5p1}
      - LLM_BASE_URL=${LLM_BASE_URL:-https://api.fireworks.ai/inference/v1}
      - MAX_TRANSCRIPT_CHARS=${MAX_TRANSCRIPT_CHARS:-50000}
      - LLM_TIMEOUT_SECONDS=${LLM_TIMEOUT_SECONDS:-60}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:5173,http://localhost}
```

- [ ] **Step 2: Write `.env.example`**

```
# Required
FIREWORKS_API_KEY=

# Optional (defaults shown)
LLM_MODEL=accounts/fireworks/models/glm-5p1
LLM_BASE_URL=https://api.fireworks.ai/inference/v1
MAX_TRANSCRIPT_CHARS=50000
LLM_TIMEOUT_SECONDS=60
CORS_ORIGINS=http://localhost:5173,http://localhost
```

- [ ] **Step 3: Smoke-test compose**

```bash
cp .env.example .env
# Edit .env to set FIREWORKS_API_KEY=placeholder (any non-empty value is fine for this smoke)
docker compose up --build -d
sleep 5
curl -sf http://localhost:8000/healthz
docker compose down
```

Expected: prints `{"status":"ok"}`.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "add docker compose and env example"
```

---

## Task 17: end-to-end smoke test against real LLM

This task is **optional** but recommended before declaring the backend done. It hits the real Fireworks endpoint.

- [ ] **Step 1: Ensure `.env` has a real `FIREWORKS_API_KEY`**

- [ ] **Step 2: Start the stack**

```bash
docker compose up --build -d
```

- [ ] **Step 3: Send a sample transcript**

```bash
curl -sf -X POST http://localhost:8000/extract \
  -H 'Content-Type: application/json' \
  -d '{"transcript": "Dr. Patel saw Bella, a 4-year-old female spayed Labrador, today for her annual wellness exam. Temperature 101.4F, heart rate 84, respiratory rate 24. Administered DA2PP and rabies boosters. Recheck in one year."}' \
  | python -m json.tool
```

Expected: a JSON response with an `events` array containing at least a history event, a vitals event, a treatment event (vaccines), and a recommendation event.

- [ ] **Step 4: Tear down**

```bash
docker compose down
```

- [ ] **Step 5: No commit** (smoke test only). If the response shows obvious extraction issues, file them as follow-up tasks rather than tweaking the prompt mid-plan.

---

## Task 18: add README

**Files:**
- Create: `README.md` (repo root)

- [ ] **Step 1: Write `README.md`**

```markdown
# vetrec — case timeline extractor

Paste a plain-text veterinary consultation transcript and get a structured
chronological case timeline. FastAPI + BAML on the backend, GLM 5.1 via
Fireworks for extraction. Frontend follows in a separate iteration.

## Quick start (Docker)

```bash
cp .env.example .env
# fill in FIREWORKS_API_KEY in .env
docker compose up --build
```

The API is at `http://localhost:8000`.

## Local development (no Docker)

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Tests:

```bash
cd backend
uv run pytest
```

BAML test fixtures (real LLM, needs API key):

```bash
cd backend
uv run baml-cli test
```

Regenerate the BAML client after editing `.baml` files:

```bash
cd backend
uv run baml-cli generate
```

## LLM configuration

| Env var | Default | Notes |
|---|---|---|
| `FIREWORKS_API_KEY` | required | Fireworks console key |
| `LLM_MODEL` | `accounts/fireworks/models/glm-5p1` | swap to any model on Fireworks |
| `LLM_BASE_URL` | `https://api.fireworks.ai/inference/v1` | swap to any OpenAI-compatible endpoint |
| `MAX_TRANSCRIPT_CHARS` | `50000` | rejects oversized input with 422 |
| `LLM_TIMEOUT_SECONDS` | `60` | per-request timeout |
| `CORS_ORIGINS` | `http://localhost:5173` | comma-separated |

Switching providers: point `LLM_BASE_URL` and `LLM_MODEL` at any OpenAI-compatible API
(OpenAI, Ollama, vLLM, etc.) and supply that provider's key as `FIREWORKS_API_KEY`.

## API

### `POST /extract`

Request:
```json
{ "transcript": "Mrs. Smith presented Buddy..." }
```

Response (200):
```json
{
  "events": [
    {"type": "history", "order": 0, "title": "...", "description": "..."},
    {"type": "vitals", "order": 1, "title": "...", "description": "...",
     "temperature_f": 102.5, "heart_rate_bpm": 140}
  ]
}
```

Errors:

| Status | `error` | Meaning |
|---|---|---|
| 422 | `transcript_empty` | empty or whitespace-only input |
| 422 | `transcript_too_long` | exceeds `MAX_TRANSCRIPT_CHARS` |
| 500 | `extraction_failed` | LLM output failed schema validation |
| 502 | `llm_unavailable` | provider transport or HTTP error |
| 504 | `llm_timeout` | exceeded `LLM_TIMEOUT_SECONDS` |

### `GET /healthz`

Liveness probe. Returns `{"status": "ok"}`. Does not call the LLM.

## Design decisions

- **Stateless.** No database, no persistence. Paste → extract → render → done.
  Matches the requirement's described flow with the smallest surface area.
- **Discriminated union with typed details.** A single `Event[]` array carries the
  timeline in transcript order; each variant has type-specific fields (Vitals
  has numeric fields, Diagnostic has a decision status, etc.). Single
  chronological list for the timeline view, full BAML type-safety per event.
- **Two status enums.** `DecisionStatus` (Approved / Declined / Pending) for
  things the clinician proposes; `ProgressStatus` (Completed / InProgress /
  Pending) for things mid-course. The requirement conflates these; splitting
  them models the real semantic difference.
- **Explicit `order: int` field** instead of relying on array order. Gives a
  deterministic sort key and a sanity-check signal.
- **Blocking `POST /extract`.** Transcripts of expected length finish in a few
  seconds. Streaming or job-queue patterns are documented as future work.
- **BAML test blocks** double as prompt regression tests. They run against the
  real LLM in CI when an API key is present, and are skipped otherwise.

## What I would extend with more time

- Streaming `/extract` via SSE so events appear as they're parsed.
- Persistence (`cases`, `events` tables on Postgres) + revisit-by-id.
- Vitals trending across multiple cases for the same patient.
- BAML evals against a labeled gold dataset rather than smoke fixtures.
- Frontend (see follow-up plan).
- Swap hand-typed frontend types for BAML's generated TypeScript client.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "add readme"
```

---

## Task 19: add evals harness

Adds an automated evaluation suite that runs the real LLM against labeled fixtures and asserts on structured facts (event counts, required event types, specific numeric vitals with strict equality, decision statuses on diagnostics/treatments). Gated behind a pytest marker so it never runs during normal test runs; needs a real `FIREWORKS_API_KEY`.

**Design decisions:**
- Strict equality on numeric vitals (`temperature_f == 101.4`). Catches drift fast.
- Extra events the fixture didn't list are allowed silently. Evals only check that required events / fields are present, not that the output set matches exactly.

**Files:**
- Create: `backend/evals/__init__.py`
- Create: `backend/evals/fixtures/routine_wellness.json`
- Create: `backend/evals/fixtures/gi_workup_declined.json`
- Create: `backend/evals/fixtures/emergency_in_progress.json`
- Create: `backend/evals/assertions.py`
- Create: `backend/tests/test_evals.py`
- Modify: `backend/pyproject.toml` (register `eval` marker, default-deselect)
- Modify: `README.md` (add a brief "Evals" section)

- [ ] **Step 1: Create evals package**

```bash
mkdir -p /Users/ayano/vetrec/backend/evals/fixtures
touch /Users/ayano/vetrec/backend/evals/__init__.py
```

- [ ] **Step 2: Write the three fixture files**

Each fixture is a JSON file with `name`, `transcript`, and `expected`. The `expected` block lists structural facts the LLM must satisfy. Anything not listed (e.g., extra History events) is allowed.

`backend/evals/fixtures/routine_wellness.json`:
```json
{
  "name": "routine_wellness",
  "transcript": "Dr. Patel saw Bella, a 4-year-old female spayed Labrador retriever, today for her annual wellness exam. Owner reports normal appetite, energy, and bowel movements. No coughing or sneezing. Physical exam: bright, alert, responsive. BCS 5/9, mucous membranes pink and moist, capillary refill under 2 seconds. Temperature 101.4F. Heart rate 84 bpm, regular rhythm. Respiratory rate 24, lungs clear. Discussed annual vaccines; owner approved. Administered DA2PP and rabies boosters today. Recommended heartworm prevention monthly. Recheck in one year.",
  "expected": {
    "min_event_count": 4,
    "required_event_types": ["vitals", "treatment", "recommendation"],
    "vitals": {
      "temperature_f": 101.4,
      "heart_rate_bpm": 84,
      "respiratory_rate": 24
    },
    "treatments": [
      {"name_contains": "DA2PP", "decision": "Approved"},
      {"name_contains": "rabies", "decision": "Approved"}
    ],
    "recommendation_categories": ["FollowUp"]
  }
}
```

`backend/evals/fixtures/gi_workup_declined.json`:
```json
{
  "name": "gi_workup_declined",
  "transcript": "Charlie, 8-year-old neutered male shepherd mix, presented for vomiting two days. Owner reports three episodes of yellow vomit, decreased appetite. Physical exam shows mild dehydration, mucous membranes tacky, abdomen tense on palpation. Temperature 102.8F, heart rate 110, weight 28.5 kg. Recommended CBC, chemistry panel, and abdominal radiographs to evaluate. Owner declined diagnostics today due to cost; agreed to symptomatic treatment. Started maropitant 1 mg/kg subq, given in clinic. Recommended bland diet for 48 hours. Recheck if vomiting persists or worsens.",
  "expected": {
    "min_event_count": 4,
    "required_event_types": ["vitals", "diagnostic", "treatment"],
    "vitals": {
      "temperature_f": 102.8,
      "heart_rate_bpm": 110,
      "weight_kg": 28.5
    },
    "diagnostics": [
      {"test_name_contains": "CBC", "decision": "Declined"}
    ],
    "treatments": [
      {"name_contains": "maropitant", "decision": "Approved"}
    ],
    "recommendation_categories": ["Diet"]
  }
}
```

`backend/evals/fixtures/emergency_in_progress.json`:
```json
{
  "name": "emergency_in_progress",
  "transcript": "Max, 6-year-old intact male boxer, brought in after being struck by a car 30 minutes ago. On presentation: tachycardic at 180 bpm, respiratory rate 60 with shallow breathing, mucous membranes pale, CRT 3 seconds, temperature 99.1F. Mentation dull. Triage exam reveals abrasions on right thoracic wall and right pelvic limb lameness. Placed IV catheter, started lactated ringers bolus 20 mL/kg, currently in progress. Recommended chest radiographs and abdominal FAST scan; owner approved. Considering opioid analgesia pending stabilization.",
  "expected": {
    "min_event_count": 4,
    "required_event_types": ["vitals", "physical_exam", "treatment", "diagnostic"],
    "vitals": {
      "heart_rate_bpm": 180,
      "respiratory_rate": 60,
      "temperature_f": 99.1,
      "capillary_refill_seconds": 3
    },
    "treatments": [
      {"name_contains": "lactated", "progress": "InProgress"}
    ],
    "diagnostics": [
      {"test_name_contains": "radiograph", "decision": "Approved"}
    ]
  }
}
```

- [ ] **Step 3: Implement `backend/evals/assertions.py`**

```python
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
```

Note on `str(e.decision)` / `str(e.category)`: BAML enums in Python render as `EnumName.Value` via `str()`. The `decision in d` substring check tolerates whichever format the installed BAML version uses.

- [ ] **Step 4: Implement `backend/tests/test_evals.py`**

```python
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
```

- [ ] **Step 5: Register the `eval` marker in `backend/pyproject.toml`**

Update the `[tool.pytest.ini_options]` table to add a marker registration and default-deselect it:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = [".", "evals"]
markers = [
    "eval: hits the real LLM; needs FIREWORKS_API_KEY. Deselected by default.",
]
addopts = "-m 'not eval'"
```

Note `pythonpath` now includes `"evals"` so `from evals.assertions import ...` resolves. Adjust the import in the test file if you prefer a different path layout.

- [ ] **Step 6: Verify normal test run still skips evals**

```bash
cd /Users/ayano/vetrec/backend && uv run pytest -v
```

Expected: 21 passed (the existing non-eval suite). No "eval" tests should run. No collection errors.

- [ ] **Step 7: Run the evals against the real LLM**

```bash
cd /Users/ayano/vetrec/backend && uv run pytest -m eval -v
```

Expected: 3 tests, ideally all passing. If any fail, report DONE_WITH_CONCERNS with the failure details — do NOT modify the prompt, schema, or fixtures to make them pass; that's a follow-up.

If 1-2 fixtures fail with reasonable LLM variance (e.g., decision wording slightly differs), report the specifics. We can tighten or loosen fixtures based on actual output.

- [ ] **Step 8: Update README**

Insert this section after the "Local development (no Docker)" → "Tests" block, before the "BAML test fixtures" block:

```markdown
Evals (real LLM, needs API key):

```bash
cd backend
uv run pytest -m eval
```

Evals are deselected from the default test run. They live in `backend/evals/`
with one JSON fixture per scenario (transcript + expected structural facts) and
a pytest parametrized runner.
```

- [ ] **Step 9: Commit in two separate logical commits**

Per project conventions (one logical change per commit), split:

```bash
cd /Users/ayano/vetrec
git add backend/evals/ backend/tests/test_evals.py backend/pyproject.toml
git commit -m "add evals harness"

git add README.md
git commit -m "document eval suite in readme"
```

## Self-review for Task 19

- All fixture JSONs parse and have `name`, `transcript`, `expected` keys?
- `assertions.py` handles missing optional fixture sections gracefully (each `assert_*` is only called if its key is present in `expected`)?
- Normal `uv run pytest` shows 21 passed (no evals run)?
- `uv run pytest -m eval` shows 3 tests collected (passing or failing — both are valid outcomes for this task)?
- Two commits: `add evals harness` and `document eval suite in readme`?
- No AI attribution anywhere?

---

## Self-review checklist (for the executor)

Before declaring the plan complete, verify:

- [ ] `uv run pytest -v` passes locally.
- [ ] `docker compose up --build` brings up the api service and `/healthz` returns ok.
- [ ] With a real key in `.env`, `POST /extract` returns sensible events on the sample transcript in Task 17.
- [ ] `git log --oneline` shows ~18 granular commits, each lowercase imperative and AI-free.

---

## Out of scope (deferred to follow-up plans)

- Frontend (React + Vite + Tailwind + React Query) — separate spec + plan.
- Persistence — separate spec.
- Streaming or job-queue extraction — separate spec.
