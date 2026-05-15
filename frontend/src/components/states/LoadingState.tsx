import { Skeleton, Stack } from "@mui/material";

export function LoadingState() {
  return (
    <Stack spacing={2} sx={{ py: 2 }}>
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} variant="rectangular" height={88} />
      ))}
    </Stack>
  );
}
