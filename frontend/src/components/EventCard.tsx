import type { JSX } from "react";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import type {
  DiagnosticEvent,
  PhysicalExamEvent,
  RecommendationEvent,
  TimelineEvent,
  TreatmentEvent,
  VitalsEvent,
} from "../api/types";

interface Props {
  event: TimelineEvent;
}

export function EventCard({ event }: Props) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" component="h3" fontWeight={600}>
          {event.title}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {event.description}
        </Typography>
        <Box sx={{ mt: 1.5 }}>{renderDetails(event)}</Box>
      </CardContent>
    </Card>
  );
}

function renderDetails(event: TimelineEvent) {
  switch (event.type) {
    case "history":
      return null;
    case "physical_exam":
      return <PhysicalExamDetails event={event} />;
    case "vitals":
      return <VitalsDetails event={event} />;
    case "diagnostic":
      return <DiagnosticDetails event={event} />;
    case "treatment":
      return <TreatmentDetails event={event} />;
    case "recommendation":
      return <RecommendationDetails event={event} />;
  }
}

function PhysicalExamDetails({ event }: { event: PhysicalExamEvent }) {
  if (!event.findings_by_system) return null;
  return (
    <Typography variant="body2" color="text.primary">
      {event.findings_by_system}
    </Typography>
  );
}

const VITALS_LABELS: Array<[keyof VitalsEvent, string, string]> = [
  ["temperature_f", "Temp", "°F"],
  ["heart_rate_bpm", "HR", "bpm"],
  ["respiratory_rate", "RR", "/min"],
  ["weight_kg", "Weight", "kg"],
  ["capillary_refill_seconds", "CRT", "s"],
];

function VitalsDetails({ event }: { event: VitalsEvent }) {
  const chips: JSX.Element[] = [];
  for (const [field, label, unit] of VITALS_LABELS) {
    const value = event[field];
    if (value !== null && value !== undefined) {
      chips.push(
        <Chip
          key={field}
          size="small"
          label={`${label}: ${value} ${unit}`}
          variant="outlined"
        />
      );
    }
  }
  if (event.mucous_membranes) {
    chips.push(
      <Chip
        key="mucous_membranes"
        size="small"
        label={`MM: ${event.mucous_membranes}`}
        variant="outlined"
      />
    );
  }
  if (chips.length === 0) return null;
  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      {chips}
    </Stack>
  );
}

function decisionColor(
  decision: "Approved" | "Declined" | "Pending"
): "success" | "error" | "default" {
  if (decision === "Approved") return "success";
  if (decision === "Declined") return "error";
  return "default";
}

function DiagnosticDetails({ event }: { event: DiagnosticEvent }) {
  return (
    <Stack spacing={1}>
      <Typography variant="body2" fontWeight={600}>
        {event.test_name}
      </Typography>
      <Stack direction="row" spacing={1}>
        <Chip
          size="small"
          label={event.decision}
          color={decisionColor(event.decision)}
        />
      </Stack>
      {event.indication && (
        <Typography variant="caption" color="text.secondary">
          Indication: {event.indication}
        </Typography>
      )}
      {event.result && (
        <Typography variant="body2">Result: {event.result}</Typography>
      )}
    </Stack>
  );
}

function TreatmentDetails({ event }: { event: TreatmentEvent }) {
  const doseLine = [event.dose, event.route].filter(Boolean).join(" — ");
  return (
    <Stack spacing={1}>
      <Typography variant="body2" fontWeight={600}>
        {event.name}
      </Typography>
      {doseLine && (
        <Typography variant="caption" color="text.secondary">
          {doseLine}
        </Typography>
      )}
      <Stack direction="row" spacing={1}>
        <Chip
          size="small"
          label={event.decision}
          color={decisionColor(event.decision)}
        />
        {event.progress && (
          <Chip size="small" label={event.progress} variant="outlined" />
        )}
      </Stack>
    </Stack>
  );
}

function RecommendationDetails({ event }: { event: RecommendationEvent }) {
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <Chip size="small" label={event.category} />
      {event.specifics && (
        <Typography variant="body2">{event.specifics}</Typography>
      )}
    </Stack>
  );
}
