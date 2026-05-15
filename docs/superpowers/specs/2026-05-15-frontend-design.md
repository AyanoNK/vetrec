# Case Timeline Frontend — Design Spec

## Overview

A single-page React app that lets a clinician paste a plain-text veterinary
consultation transcript, sends it to the backend's `POST /api/extract`, and
renders the returned structured events as a vertical timeline. No login, no
persistence, no routing. The backend (see
`docs/superpowers/specs/2026-05-14-case-timeline-design.md`) is already complete.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Bundler / framework | Vite + React 18 + TypeScript | Standard modern stack, fast dev loop. |
| Component library | Material UI (`@mui/material`, `@mui/lab`, `@mui/icons-material`) | Trusted, well-supported. Provides timeline, form inputs, layout, alerts in one package. |
| Timeline component | `Timeline` from `@mui/lab` | Most trusted React timeline. Stable enough to ship despite the `lab` label. |
| Forms | `react-hook-form` + `zod` via `@hookform/resolvers/zod` | RHF for ergonomics; zod for schema-as-source-of-truth and TS type inference. |
| Server state | `@tanstack/react-query` (`useMutation`) | Standardized loading/error/success states, ready to grow if we add endpoints. |
| Routing | None | Single page. |
| Styling | MUI defaults + `sx` prop where needed | No custom palette, no Tailwind, no global CSS framework. |
| Testing | Vitest + React Testing Library + MSW | Vitest for the Vite-native runner; RTL for component tests; MSW to intercept `fetch`. 80% coverage gate. |
| API client | Hand-written `fetch` wrapper | One endpoint; no need for a generated client. |
| Type sync | Hand-typed TS union mirroring BAML schema | ~80 lines, easy to keep in sync. Both sides change together. Can swap to BAML's TS generator later. |
| Dev → backend | Vite proxy `/api/*` → `http://localhost:8000/*` | Frontend code uses `/api/...` paths everywhere; same shape in dev (vite proxy) and prod (nginx proxy). No `VITE_API_BASE_URL` needed. |
| Production serve | nginx container | Standard pattern. Two containers (`api`, `web`). nginx serves the SPA bundle and proxies `/api/*` to the api container. |

## Architecture

```
+----------------------+        /api/extract       +----------------------+
| web (nginx)          |  -----------------------> | api (uvicorn)        |
| nginx + dist/        |                            | FastAPI + BAML       |
|  - serves SPA        |                            |  - /extract          |
|  - SPA fallback      |  <-----------------------  |  - /healthz          |
|  - proxies /api/*    |        200 { events }      |                      |
+----------------------+                            +----------------------+
```

In production: `web` serves the built React bundle and proxies `/api/*` to
`api` over the compose network. In dev: `vite` serves the SPA on `:5173` with
HMR, and proxies `/api/*` to `http://localhost:8000`. Either way, the
frontend's code always fetches `/api/extract` — no environment-specific URLs.

## Project layout

```
frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts          # React plugin, dev proxy, Vitest config
├── index.html
├── Dockerfile              # multi-stage: node build -> nginx serve
├── nginx.conf
└── src/
    ├── main.tsx            # ReactDOM mount; QueryClientProvider; CssBaseline
    ├── App.tsx             # composition root: header + form + states/timeline
    ├── api/
    │   ├── client.ts       # postExtract; ExtractError
    │   └── types.ts        # discriminated union: TimelineEvent, Timeline, ApiError
    ├── hooks/
    │   └── useExtractTimeline.ts
    ├── components/
    │   ├── TranscriptForm.tsx       # RHF + zod + MUI TextField/Button
    │   ├── TimelineView.tsx         # MUI <Timeline> per event
    │   ├── EventCard.tsx            # switches on event.type
    │   └── states/
    │       ├── EmptyState.tsx
    │       ├── LoadingState.tsx
    │       └── ErrorAlert.tsx
    ├── lib/
    │   └── eventStyling.ts          # event.type -> { color, icon, label }
    └── test/
        ├── setup.ts                 # jest-dom matchers; MSW server lifecycle
        ├── handlers.ts              # default MSW handlers
        └── utils.tsx                # renderWithProviders helper
```

## Types and API client

### `src/api/types.ts`

Hand-typed discriminated union mirroring the backend BAML schema. Every event
variant has a literal `type` discriminator that drives the TS narrowing in
renderers and gives `switch(event.type)` exhaustive coverage.

```typescript
export type DecisionStatus = "Approved" | "Declined" | "Pending";
export type ProgressStatus = "Completed" | "InProgress" | "Pending";
export type RecommendationCategory =
  | "Vaccine" | "Medication" | "Diet" | "FollowUp" | "Other";

interface BaseEvent {
  order: number;
  title: string;
  description: string;
}

export interface HistoryEvent extends BaseEvent { type: "history"; }

export interface PhysicalExamEvent extends BaseEvent {
  type: "physical_exam";
  findings_by_system: string | null;
}

export interface VitalsEvent extends BaseEvent {
  type: "vitals";
  temperature_f: number | null;
  heart_rate_bpm: number | null;
  respiratory_rate: number | null;
  weight_kg: number | null;
  mucous_membranes: string | null;
  capillary_refill_seconds: number | null;
}

export interface DiagnosticEvent extends BaseEvent {
  type: "diagnostic";
  test_name: string;
  indication: string | null;
  decision: DecisionStatus;
  result: string | null;
}

export interface TreatmentEvent extends BaseEvent {
  type: "treatment";
  name: string;
  dose: string | null;
  route: string | null;
  decision: DecisionStatus;
  progress: ProgressStatus | null;
}

export interface RecommendationEvent extends BaseEvent {
  type: "recommendation";
  category: RecommendationCategory;
  specifics: string | null;
}

export type TimelineEvent =
  | HistoryEvent | PhysicalExamEvent | VitalsEvent
  | DiagnosticEvent | TreatmentEvent | RecommendationEvent;

export interface Timeline { events: TimelineEvent[]; }

export interface ApiError {
  error:
    | "transcript_empty" | "transcript_too_long"
    | "extraction_failed" | "llm_unavailable" | "llm_timeout" | "internal";
  detail?: string;
  length?: number;
  max_length?: number;
}
```

### `src/api/client.ts`

```typescript
import type { Timeline, ApiError } from "./types";

export class ExtractError extends Error {
  constructor(public status: number, public body: ApiError) {
    super(body.detail ?? body.error);
  }
}

export async function postExtract(transcript: string): Promise<Timeline> {
  const res = await fetch("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript }),
  });
  if (!res.ok) {
    const body = (await res.json()) as ApiError;
    throw new ExtractError(res.status, body);
  }
  return res.json() as Promise<Timeline>;
}
```

## Form: TranscriptForm

react-hook-form + zod schema. The schema mirrors the backend's validation
(empty rejected, max 50,000 chars).

```typescript
import { z } from "zod";

export const TRANSCRIPT_MAX_CHARS = 50_000;

export const transcriptSchema = z.object({
  transcript: z
    .string()
    .trim()
    .min(1, "Paste a transcript to extract a timeline.")
    .max(
      TRANSCRIPT_MAX_CHARS,
      `Transcript exceeds ${TRANSCRIPT_MAX_CHARS.toLocaleString()} characters.`
    ),
});

export type TranscriptInput = z.infer<typeof transcriptSchema>;
```

UI:
- MUI `TextField` multiline (~10 rows), registered via `useForm` + `zodResolver`.
- Inline error rendered from `formState.errors.transcript`.
- Character counter `"12,345 / 50,000"` under the field; turns warning color past 90%.
- Submit button disabled while `mutation.isPending` or `formState.isSubmitting`.
- Separate "Clear" button calls `form.reset()` and `mutation.reset()`.

## Timeline rendering

`TimelineView` receives `Timeline` (or returns null when undefined). It maps
`events` (already sorted by `order` on the backend) to MUI `<TimelineItem>`s:

- `TimelineOppositeContent`: small `order` label and a type pill (e.g. `Vitals`).
- `TimelineSeparator`: `TimelineDot` (color + icon from `eventStyling.ts`) + `TimelineConnector`.
- `TimelineContent`: `<EventCard event={event} />`.

`EventCard` switches on `event.type`:
- All variants render title + description.
- `vitals`: grid of numeric chips rendering only the non-null fields.
- `diagnostic`: test_name as a subheader, decision Chip (green/red/grey), optional result text.
- `treatment`: name + dose/route line, decision Chip, progress Chip if present.
- `recommendation`: category Chip + specifics.
- `physical_exam`: `findings_by_system` as text if present.
- `history`: title + description only.

`eventStyling.ts` is the single source of per-type color + icon mapping. No
JSX, just a `Record<TimelineEvent["type"], { color, icon, label }>`. Icon
names map to `@mui/icons-material` imports at usage sites.

## Composition root

```typescript
// App.tsx
<Container maxWidth="md">
  <Header />
  <TranscriptForm onSubmit={mutation.mutate} disabled={mutation.isPending} />
  {mutation.error && <ErrorAlert error={mutation.error} />}
  {mutation.isPending && <LoadingState />}
  {mutation.data && <TimelineView timeline={mutation.data} />}
  {!mutation.data && !mutation.isPending && !mutation.error && <EmptyState />}
</Container>
```

Exactly one of `EmptyState | LoadingState | ErrorAlert | TimelineView` renders
at a time. The transcript field stays populated across renders so the user can
edit and resubmit after errors.

## Error handling

`ExtractError.body.error` maps to user-facing messages:

```typescript
const MESSAGES: Record<ApiError["error"], string> = {
  transcript_empty:     "Paste a transcript to extract a timeline.",
  transcript_too_long:  "Transcript is too long. Trim it and try again.",
  extraction_failed:    "The LLM returned an unusable response. Try again or shorten the transcript.",
  llm_unavailable:      "The extraction service is unavailable right now. Try again in a moment.",
  llm_timeout:          "The extraction took too long and timed out. Try a shorter transcript.",
  internal:             "Something went wrong on our side.",
};
```

`ErrorAlert` renders an MUI `<Alert severity="error">` with the mapped
message. For `transcript_too_long`, it also includes the `length` and
`max_length` from the response body. Non-`ExtractError` errors (network
failures, unparseable responses) fall back to `"Something went wrong."`.

## Testing

### Stack

- `vitest` — test runner, Vite-native config.
- `@testing-library/react` — render and query API.
- `@testing-library/jest-dom` — DOM matchers.
- `@testing-library/user-event` — realistic user interactions.
- `jsdom` — DOM environment.
- `msw` — `fetch` interception so tests exercise the real `postExtract` code path.

### Vitest config (inside `vite.config.ts`)

```typescript
test: {
  globals: true,
  environment: "jsdom",
  setupFiles: ["./src/test/setup.ts"],
  coverage: {
    provider: "v8",
    reporter: ["text", "html"],
    include: ["src/**/*.{ts,tsx}"],
    exclude: ["src/main.tsx", "src/**/*.test.{ts,tsx}", "src/test/**"],
    thresholds: { lines: 80, branches: 80, functions: 80, statements: 80 },
  },
}
```

80% threshold mirrors the backend.

### Setup

`src/test/setup.ts` imports `@testing-library/jest-dom/vitest`, starts the MSW
server in `beforeAll`, resets handlers in `afterEach`, closes the server in
`afterAll`.

`src/test/utils.tsx` exports a `renderWithProviders(ui)` helper that wraps in
`<QueryClientProvider>` with a fresh QueryClient per render (no cross-test
leak).

`src/test/handlers.ts` defines default MSW handlers. The "happy path" handler
returns a small Timeline fixture (history + vitals + treatment) sufficient to
verify rendering. Error handlers are set per-test via `server.use(...)`.

### Coverage

| Subject | What it verifies |
|---|---|
| `api/client.test.ts` | `postExtract` calls `/api/extract` with the correct body; returns Timeline on 200; throws `ExtractError` on 4xx/5xx; handles network failure |
| `hooks/useExtractTimeline.test.tsx` | Mutation reaches success on 200; reaches error on backend error; `isPending` toggles correctly |
| `components/TranscriptForm.test.tsx` | Submit disabled on empty input; zod error renders inline; char counter updates; `onSubmit` receives trimmed transcript; Clear wipes form and previous result |
| `components/TimelineView.test.tsx` | One `TimelineItem` per event; respects input order |
| `components/EventCard.test.tsx` | One test per variant; title + description always render; type-specific fields render when present; null fields don't leak to the DOM |
| `components/states/ErrorAlert.test.tsx` | Each of the 6 `ApiError.error` codes renders the right message; `transcript_too_long` includes the actual length/max |
| `App.test.tsx` (integration) | Full flow: render → type → submit → MSW serves Timeline → timeline renders. Plus empty submit. Plus 502 → ErrorAlert |

### Commands

```bash
npm test            # vitest watch
npm test -- --run   # single CI run
npm run coverage    # vitest --coverage
```

## Deployment

### `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### `frontend/nginx.conf`

```nginx
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri $uri/ /index.html;
  }

  location /api/ {
    proxy_pass http://api:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
  }
}
```

The trailing slash on `proxy_pass http://api:8000/` strips the `/api/` prefix,
so the frontend's `POST /api/extract` lands as `POST /extract` on the backend.
The 300s read/send timeouts tolerate slow LLM calls.

### `vite.config.ts` dev proxy

Mirrors the same shape:

```typescript
server: {
  proxy: {
    "/api": {
      target: "http://localhost:8000",
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ""),
    },
  },
}
```

### `docker-compose.yml` update

Add the `web` service:

```yaml
services:
  api:
    # ... (existing)
  web:
    build: ./frontend
    ports: ["5173:80"]
    depends_on: [api]
```

`web` resolves `api` via the compose-internal DNS name, which is why
`proxy_pass http://api:8000/` works. No `VITE_API_BASE_URL` needed — relative
`/api/...` paths work in both dev and prod.

## Out of scope (this iteration)

- Authentication.
- Routing or multi-page navigation.
- Persistence (case list, revisit-by-id).
- Streaming or progressive event rendering.
- Theming / dark mode / custom palette.
- Internationalization.
- Accessibility audits beyond what MUI provides by default.
- BAML's TS-generated client wired in (hand-typed for now).

## Future work

- Swap hand-typed types for BAML's generated TS client.
- Streaming via SSE so events appear as they're parsed.
- Persistence-backed views (when the backend gains persistence).
- A "Load sample transcript" affordance pulling from the backend's eval fixtures.
- Custom MUI theme aligned with a future product brand.
