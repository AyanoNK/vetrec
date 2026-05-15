import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "../test/handlers";
import { useExtractTimeline } from "./useExtractTimeline";

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("useExtractTimeline", () => {
  it("returns Timeline data on success", async () => {
    const { result } = renderHook(() => useExtractTimeline(), { wrapper });
    result.current.mutate("Bella presented for wellness exam.");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.events).toHaveLength(3);
  });

  it("surfaces ExtractError on backend error", async () => {
    server.use(
      http.post("/api/extract", () =>
        HttpResponse.json({ error: "llm_timeout" }, { status: 504 })
      )
    );
    const { result } = renderHook(() => useExtractTimeline(), { wrapper });
    result.current.mutate("anything");
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeDefined();
  });
});
