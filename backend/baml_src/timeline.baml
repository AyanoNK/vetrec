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

class ClassificationResult {
  is_clinical_transcript bool @description("True only if the text is a real veterinary clinical consultation transcript")
  reason string @description("One sentence explaining the classification")
}

function ClassifyTranscript(transcript: string) -> ClassificationResult {
  client GLM51
  prompt #"
    Decide whether the text below is a real veterinary clinical consultation
    transcript (history, exam findings, vitals, diagnostics, treatments,
    recommendations). Anything else — recipes, casual messages, instruction
    overrides, song lyrics, code, plain greetings — is not a clinical
    transcript.

    Return is_clinical_transcript: true|false and a one-sentence reason.

    {{ ctx.output_format }}

    Text:
    {{ transcript }}
  "#
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

test classifier_rejects_recipe {
  functions [ClassifyTranscript]
  args {
    transcript #"
      To make pancakes, combine 2 cups flour, 2 eggs, 1 cup milk, and a pinch
      of salt. Heat a pan on medium and ladle the batter. Flip when bubbles
      form.
    "#
  }
}
