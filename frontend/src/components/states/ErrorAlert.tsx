import { Alert, AlertTitle, Typography } from "@mui/material";
import { ExtractError } from "../../api/client";
import type { ApiErrorCode } from "../../api/types";

const MESSAGES: Record<ApiErrorCode, string> = {
  transcript_empty: "Paste a transcript to extract a timeline.",
  transcript_too_long: "Transcript is too long. Trim it and try again.",
  not_clinical_transcript: "This doesn't look like a veterinary consultation transcript.",
  rate_limited: "Too many requests. Wait a moment and try again.",
  extraction_failed:
    "The LLM returned an unusable response. Try again or shorten the transcript.",
  llm_unavailable:
    "The extraction service is unavailable right now. Try again in a moment.",
  llm_timeout:
    "The extraction took too long and timed out. Try a shorter transcript.",
  internal: "Something went wrong on our side.",
};

interface Props {
  error: unknown;
}

export function ErrorAlert({ error }: Props) {
  if (error instanceof ExtractError) {
    const message = MESSAGES[error.body.error];
    return (
      <Alert severity="error" sx={{ my: 2 }}>
        <AlertTitle>Extraction failed</AlertTitle>
        <Typography variant="body2">{message}</Typography>
        {error.body.error === "transcript_too_long" &&
          typeof error.body.length === "number" &&
          typeof error.body.max_length === "number" && (
            <Typography variant="caption" color="text.secondary">
              {error.body.length.toLocaleString()} /{" "}
              {error.body.max_length.toLocaleString()} characters
            </Typography>
          )}
        {error.body.error === "not_clinical_transcript" &&
          typeof error.body.reason === "string" && (
            <Typography variant="caption" color="text.secondary">
              {error.body.reason}
            </Typography>
          )}
      </Alert>
    );
  }
  return (
    <Alert severity="error" sx={{ my: 2 }}>
      <AlertTitle>Extraction failed</AlertTitle>
      <Typography variant="body2">Something went wrong.</Typography>
    </Alert>
  );
}
