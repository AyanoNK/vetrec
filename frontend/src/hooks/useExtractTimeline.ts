import { useMutation } from "@tanstack/react-query";
import { ExtractError, postExtract } from "../api/client";
import type { Timeline } from "../api/types";

export function useExtractTimeline() {
  return useMutation<Timeline, ExtractError, string>({
    mutationFn: (transcript) => postExtract(transcript),
  });
}
