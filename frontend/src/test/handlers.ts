import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

// Default "happy path" handler returning a small Timeline fixture.
// Tests can override per-test via server.use(...).
export const defaultHandlers = [
  http.post("/api/extract", async () => {
    return HttpResponse.json({
      events: [
        {
          type: "history",
          order: 0,
          title: "Presenting complaint",
          description: "Vomiting for two days.",
        },
        {
          type: "vitals",
          order: 1,
          title: "Vital signs",
          description: "Temperature elevated.",
          temperature_f: 102.8,
          heart_rate_bpm: 110,
          respiratory_rate: null,
          weight_kg: null,
          mucous_membranes: null,
          capillary_refill_seconds: null,
        },
        {
          type: "treatment",
          order: 2,
          title: "Anti-emetic administered",
          description: "Anti-emetic given subq.",
          name: "maropitant",
          dose: "1 mg/kg",
          route: "subcutaneous",
          decision: "Approved",
          progress: "Completed",
        },
      ],
    });
  }),
];

export const server = setupServer(...defaultHandlers);
