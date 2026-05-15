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
