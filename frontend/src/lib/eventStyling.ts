import type { TimelineEvent } from "../api/types";

export type EventStyleColor =
  | "primary"
  | "secondary"
  | "success"
  | "info"
  | "warning"
  | "error";

export interface EventStyle {
  color: EventStyleColor;
  icon: string;
  label: string;
}

export const EVENT_STYLES: Record<TimelineEvent["type"], EventStyle> = {
  history: { color: "info", icon: "History", label: "History" },
  physical_exam: {
    color: "primary",
    icon: "MedicalServices",
    label: "Physical Exam",
  },
  vitals: { color: "secondary", icon: "MonitorHeart", label: "Vitals" },
  diagnostic: { color: "warning", icon: "Science", label: "Diagnostic" },
  treatment: { color: "success", icon: "Medication", label: "Treatment" },
  recommendation: { color: "primary", icon: "EventNote", label: "Recommendation" },
};
