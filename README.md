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
| `RATE_LIMIT_PER_MINUTE` | `30` | per-IP cap on `/extract`; `/healthz` is exempt |

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
| 422 | `not_clinical_transcript` | classifier rejected the input as non-clinical; response includes `reason` |
| 429 | `rate_limited` | per-IP request rate exceeded `RATE_LIMIT_PER_MINUTE` |
| 500 | `extraction_failed` | LLM output failed schema validation |
| 502 | `llm_unavailable` | provider transport or HTTP error |
| 504 | `llm_timeout` | exceeded `LLM_TIMEOUT_SECONDS` |

### `GET /healthz`

Liveness probe. Returns `{"status": "ok"}`. Does not call the LLM.

## Sample transcripts

Five transcripts of varying complexity to try in the UI. They cover different species, event-type combinations, decision/progress statuses, and length. Each takes roughly 60–90 seconds to extract via GLM 5.1.

### 1. Feline wellness (simple)

History, vitals, two vaccines, one follow-up recommendation.

```
Mittens, 3-year-old female spayed domestic shorthair, presented for annual wellness exam. Owner reports normal eating, drinking, and litter box habits; indoor only. Physical exam unremarkable. BCS 5/9, mucous membranes pink and moist, capillary refill under 2 seconds. Temperature 101.0F, heart rate 180 bpm, respiratory rate 28. Administered FVRCP and rabies boosters today. Recommended dental cleaning within 6 months given grade 2 tartar. Recheck in one year.
```

### 2. Canine dermatology (moderate)

History with diet change, exam findings across multiple sites, approved cytology, multi-drug treatment plan, dietary recommendation.

```
Rocky, 5-year-old neutered male golden retriever, presented for two weeks of pruritus and scratching at the ears and ventral abdomen. Owner reports flare started after switching food brands. Physical exam: erythema and self-inflicted excoriations on the ventral abdomen and inguinal region, mild otitis externa bilaterally with brown waxy discharge. Temperature 101.6F, heart rate 96, weight 32 kg. Recommended cytology of the ear canals and a skin scrape; owner approved. Cytology revealed Malassezia overgrowth. Started ear cleanser daily for two weeks, miconazole-betamethasone otic BID for 14 days, and a 5-day course of oclacitinib 0.5 mg/kg PO BID. Recommended switching to a hydrolyzed protein diet trial for 8 weeks. Recheck in two weeks.
```

### 3. Feline chronic kidney disease (complex, declined treatment)

Long history, weight loss trend, vitals, multiple approved diagnostics, multiple ongoing medications, **one declined treatment** (capromorelin), prescription diet recommendation.

```
Whiskers, 14-year-old female spayed domestic longhair, presented for follow-up of stage 2 chronic kidney disease and to address progressive weight loss. Owner reports decreased appetite and increased water intake over the past month, no vomiting. Physical exam shows BCS 3/9 (down from 4/9 three months ago), mild dehydration, mucous membranes tacky, kidneys small and irregular on palpation. Temperature 100.8F, heart rate 200, respiratory rate 32, weight 3.4 kg (down from 3.7 kg). Recommended repeat chemistry panel, SDMA, urinalysis, and blood pressure measurement; owner approved all diagnostics. Discussed prescription renal diet; owner agreed to start Hill's k/d. Started subcutaneous fluid therapy at home, 100 mL lactated Ringer's every 48 hours; owner trained in clinic. Continued telmisartan 1 mg/kg PO SID. Recommended capromorelin 3 mg/kg PO SID for appetite stimulation; owner declined initially due to cost, will reconsider at recheck. Recheck in three weeks with repeat bloodwork.
```

### 4. Equine colic (emergency, in-progress treatment)

Different species, after-hours presentation, multiple diagnostics, IV pain control plus ongoing fluid therapy, overnight hospitalization decision.

```
Duke, 12-year-old quarter horse gelding, presented at 11 PM for acute colic of three hours' duration. Owner reports patient was rolling, pawing, and looking at flanks. On presentation: heart rate 72 bpm, respiratory rate 28, mucous membranes pale pink with capillary refill 2 seconds, temperature 99.4F. Mentation dull but responsive. Gut sounds reduced in all four quadrants. Mild abdominal distension noted. Recommended rectal palpation, nasogastric intubation, and abdominal ultrasound; owner approved. Rectal palpation revealed gas-distended large colon without obvious displacement. Nasogastric reflux negative. Ultrasound showed normal small intestine motility. Administered flunixin meglumine 1.1 mg/kg IV and butorphanol 0.05 mg/kg IV for pain. Started polyionic IV fluids at 4 L/hr via 14-gauge jugular catheter, currently in progress. Withheld feed and water pending response. Recommended overnight hospitalization for monitoring and continued fluid therapy; owner approved. Will reassess in two hours.
```

### 5. Pediatric multi-system (highly complex)

Puppy with concurrent parvovirus, hookworms, and an incidental heart murmur. Exercises every event type: history, physical exam, vitals (multiple), diagnostics (three approved), treatments (multiple in-progress), recommendations (vaccine postponed, cardiology referral, recheck labs).

```
Bella, 12-week-old intact female French bulldog, presented for routine puppy wellness and second DA2PP booster. Owner reports recent intermittent vomiting and soft stools for three days, decreased appetite today, otherwise active. Physical exam: BCS 4/9, mucous membranes pale pink, capillary refill 2 seconds, mild dehydration, soft fluid-filled small intestinal loops on abdominal palpation, slightly distended abdomen. Temperature 102.4F, heart rate 160 bpm, respiratory rate 36, weight 2.1 kg. Lung fields clear, heart auscultation reveals grade 2/6 left apical systolic murmur. Discussed concerns for parvovirus and intestinal parasitism. Recommended parvovirus SNAP test, fecal flotation, and CBC with chemistry panel; owner approved all diagnostics. Parvovirus SNAP positive. Fecal positive for hookworms. CBC showed mild leukopenia. Hospitalized for supportive care. Started lactated Ringer's IV bolus 30 mL/kg, currently in progress. Started maropitant 1 mg/kg subq SID and ampicillin-sulbactam 30 mg/kg IV TID. Postponed DA2PP booster due to active illness. Administered pyrantel pamoate 5 mg/kg PO once, repeat in two weeks. Recommended cardiology consult and echocardiogram for the heart murmur once recovered from current illness; owner approved referral. Discussed prognosis and 24-hour monitoring; owner agreed to hospitalization. Recheck CBC and chemistry tomorrow morning.
```

## Design decisions

- **Stateless for first version.** No database, no persistence. Paste → extract → render → done.
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

## Future work

- Streaming `/extract` via SSE so events appear as they're parsed.
- Persistence (`cases`, `events` tables on Postgres) + revisit-by-id.
- Vitals trending across multiple cases for the same patient.
- BAML evals against a labeled gold dataset rather than smoke fixtures.
- CI for feaure branches
