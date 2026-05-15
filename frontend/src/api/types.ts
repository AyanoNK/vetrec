export type DecisionStatus = "Approved" | "Declined" | "Pending";
export type ProgressStatus = "Completed" | "InProgress" | "Pending";
export type RecommendationCategory =
  | "Vaccine"
  | "Medication"
  | "Diet"
  | "FollowUp"
  | "Other";

interface BaseEvent {
  order: number;
  title: string;
  description: string;
}

export interface HistoryEvent extends BaseEvent {
  type: "history";
}

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
  | HistoryEvent
  | PhysicalExamEvent
  | VitalsEvent
  | DiagnosticEvent
  | TreatmentEvent
  | RecommendationEvent;

export interface Timeline {
  events: TimelineEvent[];
}

export type ApiErrorCode =
  | "transcript_empty"
  | "transcript_too_long"
  | "extraction_failed"
  | "llm_unavailable"
  | "llm_timeout"
  | "internal";

export interface ApiError {
  error: ApiErrorCode;
  detail?: string;
  length?: number;
  max_length?: number;
}
