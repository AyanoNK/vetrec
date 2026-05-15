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
  order int
  title string
  description string
}

class PhysicalExamEvent {
  type "physical_exam"
  order int
  title string
  description string
  findings_by_system string? @description("Body system findings as a comma-separated or free-text string")
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
  events (HistoryEvent | PhysicalExamEvent | VitalsEvent | DiagnosticEvent | TreatmentEvent | RecommendationEvent)[]
}

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
