# vetrec — case timeline extractor

Paste a plain-text veterinary consultation transcript and get a structured
chronological case timeline. React + MUI frontend, FastAPI + BAML backend,
GLM 5.1 via Fireworks for extraction.

## Quick start (Docker)

```bash
cp .env.example .env
# fill in FIREWORKS_API_KEY in .env
docker compose up --build
```

- Frontend at `http://localhost:5173`.
- Backend at `http://localhost:8000`.
- nginx in the web container proxies `/api/*` to the backend.

## Backend (local dev)

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

Tests run with coverage enabled by default; coverage below 80% fails the run.
For an HTML report:

```bash
cd backend
uv run pytest --cov-report=html
open htmlcov/index.html  # macOS — use xdg-open on Linux
```

Evals (real LLM, needs API key):

```bash
cd backend
uv run pytest -m eval
```

Evals are deselected from the default test run. They live in `backend/evals/`
with one JSON fixture per scenario (transcript + expected structural facts) and
a pytest parametrized runner.

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

## Frontend (local dev)

```bash
cd frontend
pnpm install
pnpm dev
```

Vite serves the SPA on `http://localhost:5173` and proxies `/api/*` to
`http://localhost:8000`. Start the backend separately (`docker compose up api`
or the local-dev backend instructions above) so the proxy has something to talk to.

Tests (Vitest + React Testing Library + MSW):

```bash
cd frontend
pnpm test            # watch mode
pnpm test:run        # single run (CI)
pnpm coverage        # 80% gate; HTML report at frontend/coverage/index.html
```

## LLM configuration

| Env var | Default | Notes |
|---|---|---|
| `FIREWORKS_API_KEY` | required | Fireworks console key |
| `LLM_MODEL` | `accounts/fireworks/models/glm-5p1` | swap to any model on Fireworks |
| `LLM_BASE_URL` | `https://api.fireworks.ai/inference/v1` | swap to any OpenAI-compatible endpoint |
| `MAX_TRANSCRIPT_CHARS` | `50000` | rejects oversized input with 422 |
| `LLM_TIMEOUT_SECONDS` | `180` | per-request timeout; GLM 5.1 calls typically take 60-90s |
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
