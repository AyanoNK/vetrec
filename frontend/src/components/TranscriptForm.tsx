import { zodResolver } from "@hookform/resolvers/zod";
import { Box, Button, Stack, TextField, Typography } from "@mui/material";
import { useForm } from "react-hook-form";
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

interface Props {
  onSubmit: (transcript: string) => void;
  onClear: () => void;
  disabled: boolean;
}

export function TranscriptForm({ onSubmit, onClear, disabled }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isValid },
  } = useForm<TranscriptInput>({
    resolver: zodResolver(transcriptSchema),
    mode: "onChange",
    defaultValues: { transcript: "" },
  });

  const transcript = watch("transcript") ?? "";
  const length = transcript.length;
  const warn = length / TRANSCRIPT_MAX_CHARS >= 0.9;
  const submit = handleSubmit((values) =>
    onSubmit(values.transcript.trim())
  );

  return (
    <Box component="form" onSubmit={submit} noValidate>
      <TextField
        id="transcript"
        label="Transcript"
        multiline
        minRows={10}
        fullWidth
        error={Boolean(errors.transcript)}
        helperText={errors.transcript?.message ?? " "}
        inputProps={{ "aria-label": "transcript" }}
        {...register("transcript")}
      />
      <Stack
        direction="row"
        spacing={2}
        alignItems="center"
        justifyContent="space-between"
        sx={{ mt: 1 }}
      >
        <Typography
          variant="caption"
          color={warn ? "warning.main" : "text.secondary"}
        >
          {length.toLocaleString()} / {TRANSCRIPT_MAX_CHARS.toLocaleString()}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button
            type="button"
            onClick={() => {
              reset({ transcript: "" });
              onClear();
            }}
            disabled={disabled}
          >
            Clear
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={disabled || !isValid}
            sx={{ "&.Mui-disabled": { pointerEvents: "auto", cursor: "default" } }}
          >
            Extract timeline
          </Button>
        </Stack>
      </Stack>
    </Box>
  );
}
