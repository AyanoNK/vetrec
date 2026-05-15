import { Box, Typography } from "@mui/material";

export function EmptyState() {
  return (
    <Box sx={{ textAlign: "center", color: "text.secondary", py: 6 }}>
      <Typography variant="body1">
        Paste a transcript above to extract a case timeline.
      </Typography>
    </Box>
  );
}
