import { Box, Container, CssBaseline, Typography } from "@mui/material";
import { useExtractTimeline } from "./hooks/useExtractTimeline";
import { TranscriptForm } from "./components/TranscriptForm";
import { TimelineView } from "./components/TimelineView";
import { EmptyState } from "./components/states/EmptyState";
import { LoadingState } from "./components/states/LoadingState";
import { ErrorAlert } from "./components/states/ErrorAlert";

export default function App() {
  const mutation = useExtractTimeline();

  return (
    <>
      <CssBaseline />
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" component="h1">
            Case Timeline
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Paste a veterinary consultation transcript and get a structured
            chronological case timeline.
          </Typography>
        </Box>

        <TranscriptForm
          onSubmit={(transcript) => mutation.mutate(transcript)}
          onClear={() => mutation.reset()}
          disabled={mutation.isPending}
        />

        {mutation.isError && <ErrorAlert error={mutation.error} />}
        {mutation.isPending && <LoadingState />}
        {mutation.isSuccess && <TimelineView timeline={mutation.data} />}
        {!mutation.isSuccess &&
          !mutation.isPending &&
          !mutation.isError && <EmptyState />}
      </Container>
    </>
  );
}
