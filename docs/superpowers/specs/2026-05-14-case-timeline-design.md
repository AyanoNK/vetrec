# Case Timeline — Design Spec

## Overview

Given a plain-text veterinary medical transcript, extract a structured chronological
timeline of the consultation and render it for an incoming clinician at shift change.
The system is end-to-end: a paste-and-go React UI, a FastAPI backend that calls a
single BAML function, and Docker Compose orchestration.

This spec covers the backend and AI layer in detail; the frontend is sketched and
will be developed in a later iteration.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Persistence | None (stateless) | Smallest surface area; matches "paste -> timeline -> done" flow. |
| LLM provider | GLM 5.1 via Fireworks (OpenAI-compatible) | User-supplied. BAML talks to it via `openai-generic` client. |
| Async UX | Blocking `POST /extract` | Transcripts of expected length finish in a few seconds. |
| Schema shape | Discriminated union with typed details | Shows BAML's structured-extraction strength without losing single-timeline ordering. |
| Backend layout | Layered FastAPI (api / services / schemas) | Standard, easy to extend; clear seams. |
| Python tooling | `uv` for deps and execution | Project-wide preference. |
| Coverage gate | `pytest-cov` always on, 80% minimum, fails the run if below | Catches drift early; chosen after the first run showed 96% baseline. |
| Eval harness | JSON-fixture-driven pytest suite, gated by `-m eval` | Real-LLM regression tests with strict numeric checks; extras allowed. |
| Frontend stack | Vite + React + TypeScript + Tailwind + React Query | Standard, fast dev loop; React Query covers async states. |
| Deployment | Docker Compose; `api` service this iteration, `web` joins with the frontend | Single command to bring up the stack. |

## Architecture

```
+--------------------+        POST /extract        +--------------------+
| web (nginx)        |  -------------------------> | api (uvicorn)      |
| React + Vite build |                              | FastAPI            |
| serves SPA, proxy  |  <-------------------------  | -> services        |
| no API logic       |        200 { events }        |    -> baml_client  |
+--------------------+                              |       -> Fireworks |
                                                    +--------------------+
```

Two containers, one shared compose network. The frontend container serves the built
SPA via nginx and proxies `/api/*` to the api container in production. In local dev,
Vite's dev server runs separately and uses CORS.

## BAML schema

One BAML file (`baml_src/timeline.baml`) plus a client file (`baml_src/clients.baml`).

### Status enums

Two distinct status concepts, intentionally split:

- `DecisionStatus` — `Approved | Declined | Pending`. For things the clinician proposes
  and the client agrees or refuses to (Diagnostics, Treatments).
- `ProgressStatus` — `Completed | InProgress | Pending`. For things that have a
  temporal completion state (a treatment course mid-administration).

### Event variants

Each variant carries shared fields `order: int`, `title: string`, `description: string`,
plus a literal `type` discriminator and variant-specific fields.

| Variant | Variant-specific fields |
|---|---|
| `HistoryEvent` | (none — `description` carries the content) |
| `PhysicalExamEvent` | `findings_by_system?: map<string, string>` |
| `VitalsEvent` | `temperature_f?: float`, `heart_rate_bpm?: int`, `respiratory_rate?: int`, `weight_kg?: float`, `mucous_membranes?: string`, `capillary_refill_seconds?: float` |
| `DiagnosticEvent` | `test_name: string`, `indication?: string`, `decision: DecisionStatus`, `result?: string` |
| `TreatmentEvent` | `name: string`, `dose?: string`, `route?: string`, `decision: DecisionStatus`, `progress?: ProgressStatus` |
| `RecommendationEvent` | `category: "vaccine" \| "medication" \| "diet" \| "follow_up" \| "other"`, `specifics?: string` |

```
type Event = HistoryEvent | PhysicalExamEvent | VitalsEvent
           | DiagnosticEvent | TreatmentEvent | RecommendationEvent

class Timeline { events: Event[] }
```

### The function

```
function ExtractTimeline(transcript: string) -> Timeline {
  client GLM51
  prompt #"
    <system instructions: extract events in transcript order,
     number them 0..N-1 via the `order` field, fill optional fields
     only when explicitly stated, do not invent values>
    {{ ctx.output_format }}
    Transcript:
    {{ transcript }}
  "#
}
```

The prompt asks the model to number events via an explicit `order: int` instead of
relying on array order. This gives a deterministic sort key and a sanity-check
signal (gaps or duplicates suggest the model misbehaved).

Two or three few-shot examples anchor extraction quality; they live in
`baml_src/timeline.baml` as `test` blocks and double as regression tests.

### Client

```
client<llm> GLM51 {
  provider openai-generic
  options {
    base_url env.LLM_BASE_URL        # https://api.fireworks.ai/inference/v1
    api_key env.FIREWORKS_API_KEY
    model env.LLM_MODEL              # accounts/fireworks/models/glm-5p1
    temperature 0.0
  }
}
```

## Backend

### Layout

```
backend/
  pyproject.toml           # uv-managed deps; pytest, coverage, and marker config
  uv.lock
  Dockerfile
  .dockerignore
  baml_src/
    clients.baml
    timeline.baml          # schema + ExtractTimeline + three test fixtures
  baml_client/             # generated, committed
  tests/
    conftest.py            # sets safe env defaults before any test imports
    test_health.py
    test_config.py
    test_errors.py
    test_extractor.py
    test_extract_route.py
    test_evals.py          # parametrized real-LLM eval suite, marker: eval
  evals/
    __init__.py
    assertions.py          # shared assertion helpers
    fixtures/*.json        # one file per scenario: transcript + expected
  app/
    main.py                # FastAPI app, CORS, exception handlers, mounts routers
    config.py              # pydantic-settings: keys, URLs, limits, CORS origins
    api/timeline.py        # POST /extract router
    services/extractor.py  # TimelineExtractor: validate, call BAML, normalize
    schemas/timeline.py    # API Pydantic models; re-export BAML types where they fit
    core/errors.py         # Domain exceptions and FastAPI handlers
```

### Configuration (env vars)

- `FIREWORKS_API_KEY` — required
- `LLM_BASE_URL` — default `https://api.fireworks.ai/inference/v1`
- `LLM_MODEL` — default `accounts/fireworks/models/glm-5p1`
- `MAX_TRANSCRIPT_CHARS` — default `50000`
- `LLM_TIMEOUT_SECONDS` — default `180` (GLM 5.1 calls typically take 60–90s; the
  earlier 60s default was too tight)
- `CORS_ORIGINS` — comma-separated; default `http://localhost:5173`

Settings are loaded via `pydantic-settings` from env vars and from a `.env` file.
The Settings class checks `.env` (working directory) and then `../.env` (parent
directory). This lets the same `.env` at the repo root serve both `docker compose`
(which expects a root-level `.env`) and `uv run pytest` invoked from `backend/`.

### Validation rules

- Reject empty or whitespace-only transcripts (422 `transcript_empty`).
- Reject transcripts exceeding `MAX_TRANSCRIPT_CHARS` (422 `transcript_too_long`).
- Sort returned events by `order` server-side as a defensive step.
- Wrap the BAML call in `LLM_TIMEOUT_SECONDS`; on exceed return 504.

### Error taxonomy

| Layer | Trigger | Response |
|---|---|---|
| Input validation (Pydantic) | bad JSON, missing fields | 422 with field details |
| Domain validation | empty, too long | 422 `{ error: "transcript_empty" \| "transcript_too_long" }` |
| BAML validation error | LLM returned non-conforming JSON | 500 `{ error: "extraction_failed" }` |
| BAML HTTP error | network, 5xx upstream | 502 `{ error: "llm_unavailable" }` |
| Timeout | exceeded `LLM_TIMEOUT_SECONDS` | 504 `{ error: "llm_timeout" }` |
| Catch-all | unexpected | 500 `{ error: "internal" }`, logged with request id |

## API contract

### `POST /extract`

Request:

```json
{ "transcript": "Mrs. Smith presented Buddy ..." }
```

Success (200):

```json
{
  "events": [
    { "type": "history", "order": 0, "title": "...", "description": "..." },
    { "type": "vitals",  "order": 1, "title": "...", "description": "...",
      "temperature_f": 102.5, "heart_rate_bpm": 140 },
    ...
  ]
}
```

Error responses follow the taxonomy above.

### `GET /healthz`

Liveness probe. Returns `{ "status": "ok" }` without calling the LLM.

## Frontend (sketch)

Deferred to a later iteration. The shape is captured here for completeness:

- Vite + React + TypeScript + Tailwind, React Query for the extraction mutation.
- One page: `TranscriptInput` + `Timeline` rendering `EventCard` per event.
- Four UI states: idle, pending (skeleton), success (timeline), error (banner).
- `EventCard` switches on `event.type` for per-variant rendering and badge display.
- Type-safe `Event` discriminated union mirroring the BAML schema; can be swapped
  for BAML's TypeScript-generated client later.

## Deployment

### `docker-compose.yml`

This iteration ships only the `api` service. The `web` service will be added
when the frontend lands; the eventual shape is shown below it.

```yaml
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - FIREWORKS_API_KEY=${FIREWORKS_API_KEY}
      - LLM_MODEL=${LLM_MODEL:-accounts/fireworks/models/glm-5p1}
      - LLM_BASE_URL=${LLM_BASE_URL:-https://api.fireworks.ai/inference/v1}
      - MAX_TRANSCRIPT_CHARS=${MAX_TRANSCRIPT_CHARS:-50000}
      - LLM_TIMEOUT_SECONDS=${LLM_TIMEOUT_SECONDS:-180}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:5173,http://localhost}
```

Eventual additional service for the frontend iteration:

```yaml
  web:
    build: ./frontend
    ports: ["5173:80"]
    depends_on: [api]
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
```

### Backend Dockerfile

Single-stage from `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`. Copy sources,
`uv sync --frozen --no-dev`, expose 8000, run `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`.

### Frontend Dockerfile

Multi-stage: `node:20-alpine` build with `npm ci && npm run build`, then
`nginx:alpine` serving `dist/` with an SPA fallback config.

## Testing

Three layers, with different latency and coverage characteristics:

1. **Python unit / integration tests** — always run. BAML is mocked, the
   extractor is mocked at the route layer, env defaults are seeded by a
   `tests/conftest.py` so module-level `Settings()` imports succeed without a
   real API key. Includes:
   - `test_health`, `test_config`, `test_errors`, `test_extractor`,
     `test_extract_route`.

2. **BAML test fixtures** — three `test` blocks in `timeline.baml`
   (`routine_wellness`, `gi_workup_declined`, `emergency_in_progress`). Run via
   `uv run baml-cli test` against the real LLM when a key is present. These are
   smoke fixtures, not asserted in detail.

3. **Eval suite** — parametrized pytest tests under `tests/test_evals.py`,
   loaded from JSON fixtures in `evals/fixtures/`. Each fixture declares a
   transcript and an `expected` block (min event count, required event types,
   specific numeric vitals with strict equality, decision/progress statuses on
   diagnostics and treatments, recommendation categories). Helpers live in
   `evals/assertions.py`. Gated by the `eval` pytest marker and deselected from
   the default run via `addopts = "-m 'not eval' ..."`. Run explicitly with
   `uv run pytest -m eval`. Extras the LLM produces beyond the fixture's
   expectations are allowed silently; the suite only checks that required facts
   are present.

### Coverage

`pytest-cov` is wired into the default `addopts`. Every `uv run pytest`
produces a terminal coverage report. The run fails if total branch coverage
drops below **80%**.

- Source: `app/` only. The generated `baml_client/`, `evals/`, and `tests/`
  themselves are excluded.
- `exclude_lines` covers `pragma: no cover`, `raise NotImplementedError`, and
  `if TYPE_CHECKING:` blocks.
- HTML report on demand: `uv run pytest --cov-report=html` writes to
  `htmlcov/` (gitignored).

## Out of scope (this iteration)

- Persistence and case revisit-by-id.
- Authentication.
- Streaming or job-queue UX.
- Real-time progress feedback to the user.
- BAML's TS client wired into the frontend (we'll start with hand-typed TS).

## Future work

- Streaming `/extract` via SSE so events appear as they're parsed.
- Postgres-backed persistence with `cases` and `events` tables.
- Vitals trending across multiple cases for the same patient.
- Expand the eval suite into a larger labeled gold dataset and add quality
  metrics (precision/recall per event type, per-field accuracy).
- Swap hand-typed frontend types for BAML's generated TS client.
