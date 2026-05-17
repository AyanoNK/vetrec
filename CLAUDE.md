# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

Two-service app for extracting structured veterinary case timelines from
plain-text consultation transcripts. **Stateless** — no database, no
persistence. Paste → extract → render → done.

- **`backend/`** — FastAPI + BAML. BAML defines the schema and prompts in
  `baml_src/*.baml` and generates a Python client into `baml_client/` (both
  `baml_src/` and the generated `baml_client/` are committed). Talks to any
  OpenAI-compatible chat endpoint via the `GLM51` client in `clients.baml`;
  defaults to GLM 5.1 on Fireworks but any provider works by swapping
  `LLM_BASE_URL` / `LLM_MODEL` / `FIREWORKS_API_KEY`.
- **`frontend/`** — React 18 + MUI 5 + TanStack Query + Vite. Single page:
  paste form → extracts via `POST /api/extract` → renders the timeline.
  Hand-typed `Timeline` mirror of the BAML schema lives in `src/api/types.ts`.
- **`docker-compose.yml`** — `api` (FastAPI on `:8000`) + `web` (nginx serving
  the built SPA on `:5173`). The nginx config proxies `/api/*` to
  `api:8000/*`. In `pnpm dev`, Vite proxies `/api/*` to `localhost:8000`
  instead.

### Extraction pipeline (two LLM calls)

`TimelineExtractor.extract()` in `app/services/extractor.py` does
**validate → classify → extract**:

1. `_validate` — rejects empty / oversize input before any LLM call.
2. `_classify` — `ClassifyTranscript` BAML function asks the LLM whether the
   text is a real clinical transcript. Non-clinical input raises
   `NotClinicalTranscriptError` (HTTP 422). Classifier output that fails
   validation also fails closed as non-clinical — *not* as a 500.
3. `_extract_events` — `ExtractTimeline` BAML function returns a `Timeline`
   whose `events` is a discriminated union of six event types
   (`history`, `physical_exam`, `vitals`, `diagnostic`, `treatment`,
   `recommendation`). Events are sorted by `order` before returning.

Both LLM calls are wrapped in `asyncio.wait_for(timeout=llm_timeout_seconds)`.

### Error model

Domain exceptions live in `app/core/errors.py` and are mapped to JSON
responses in `app/main.py` via `@app.exception_handler(...)`. The response
body is always `{"error": "<code>", "detail": "...", ...}`. The frontend
mirrors the set of codes in `src/api/types.ts` as the `ApiErrorCode` union.
**When adding a new error code, update all three sites:** the exception
class, the handler in `main.py`, and the `ApiErrorCode` union (and the README
table).

### Dependency-injection seam

`app/api/timeline.py` declares `get_extractor()` as a stub that raises
`NotImplementedError`. `app/main.py` overrides it via
`app.dependency_overrides[get_extractor] = _build_extractor` at startup.
Tests swap in a fake extractor by setting `app.dependency_overrides[...]`
themselves. Preserve this pattern — don't wire the real extractor into the
router module.

### Rate limiting

`slowapi` middleware applies `RATE_LIMIT_PER_MINUTE` (default 30) per remote
IP across all routes; `/healthz` is exempted via `@_limiter.exempt`. Hits
return HTTP 429 with `error: rate_limited`.

## BAML workflow

`.baml` files are the source of truth for the LLM schema and prompts.
`backend/baml_client/` is **generated code that is committed** — the
Dockerfile copies it rather than regenerating at build time.

- After editing `backend/baml_src/*.baml`, regenerate with
  `uv run baml-cli generate`. Commit the regenerated `baml_client/` alongside
  the `.baml` change.
- BAML `test` blocks in `timeline.baml` are real-LLM prompt regression tests.
  Run with `uv run baml-cli test` (needs `FIREWORKS_API_KEY`). They're
  separate from pytest.

## Test layers

Three layers, each with different gating and cost:

| Layer | Command | Gating | Hits real LLM? |
|---|---|---|---|
| Backend unit tests | `uv run pytest` | runs by default; **80% coverage gate** | no |
| Backend evals | `uv run pytest -m eval` | deselected by default; needs API key | **yes** |
| BAML prompt tests | `uv run baml-cli test` | manual; needs API key | **yes** |
| Frontend tests | `pnpm test` / `pnpm test:run` / `pnpm coverage` | coverage gates 80% lines/branches/functions/statements | no (MSW mocks `/api/extract`) |

Backend tests set safe default env vars in `tests/conftest.py` so importing
`app.main` doesn't blow up on missing `FIREWORKS_API_KEY`.

Eval fixtures live in `backend/evals/fixtures/*.json`; each has a
`transcript` and an `expected` block of structural assertions (min event
count, required types, vitals values, treatment/diagnostic presence,
recommendation categories). `tests/test_evals.py` parametrizes over them and
calls the real extractor. To add a scenario, drop a new JSON fixture in that
directory.

## Configuration

`app/config.py` loads settings via `pydantic-settings` from either
`backend/.env` (local dev) or `../.env` at repo root (used by
`docker compose`). `CORS_ORIGINS` accepts a comma-separated string. See the
README for the full env-var table.

## Reference docs in-repo

- `README.md` — quick-start, command cheat sheet, env vars, API contract,
  sample transcripts, design decisions.
- `docs/requirement.md` — original spec the project is built against.
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — design specs and
  implementation plans for the backend and frontend builds. Useful context
  when extending either side.

---

# Project conventions

These rules apply to all work in this repository. They sit on top of any global
rules already in place.

## Commit messages

- Start with a **lowercase** letter (`add gitignore`, not `Add gitignore`).
- **Present-tense imperative** (`add`, `fix`, `update` — never `added` or `adding`).
- Concise and direct. Keep the subject under ~50 characters.
- One logical change per commit. Split unrelated work into separate commits.
- No trailing period on the subject line.
- No AI attribution. No `Co-Authored-By: Claude` trailers.

Examples:

```
add gitignore
add fastapi extract endpoint
fix vitals parsing for missing temperature
```

## Python tooling

- Use `uv` for everything Python-related.
  - `uv sync` to install, `uv add <pkg>` to add a dep, `uv run <cmd>` to execute.
  - `pyproject.toml` declares deps; `uv.lock` is committed.
- No `requirements.txt`, no `pip install`, no Poetry, no Pipenv.

## Node / JavaScript tooling

- Use `pnpm` for everything Node/JS-related.
  - `pnpm install` to install, `pnpm add <pkg>` to add a dep, `pnpm add -D <pkg>` for a dev dep, `pnpm <script>` to run a package.json script.
  - `package.json` declares deps; `pnpm-lock.yaml` is committed.
  - CI install: `pnpm install --frozen-lockfile`.
- No `npm install`, no `yarn`. No `package-lock.json`. No `yarn.lock`.
- In Dockerfiles, enable pnpm via `RUN corepack enable` before the install step.

## Branches and pushes

- Do not push without explicit instruction.
- Do not force-push to `main`.
