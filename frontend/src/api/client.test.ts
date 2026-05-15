import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../test/handlers";
import { ExtractError, postExtract } from "./client";

describe("postExtract", () => {
  it("returns the Timeline on 200", async () => {
    const result = await postExtract("Bella presented for wellness exam.");
    expect(result.events).toHaveLength(3);
    expect(result.events[0]).toMatchObject({ type: "history", order: 0 });
  });

  it("sends the transcript as JSON to /api/extract", async () => {
    let capturedBody: unknown = null;
    server.use(
      http.post("/api/extract", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ events: [] });
      })
    );
    await postExtract("hello");
    expect(capturedBody).toEqual({ transcript: "hello" });
  });

  it("throws ExtractError with parsed body on 422", async () => {
    server.use(
      http.post("/api/extract", () =>
        HttpResponse.json(
          { error: "transcript_empty", detail: "transcript is empty" },
          { status: 422 }
        )
      )
    );

    await expect(postExtract("")).rejects.toBeInstanceOf(ExtractError);
    try {
      await postExtract("");
    } catch (err) {
      expect(err).toBeInstanceOf(ExtractError);
      const extractError = err as ExtractError;
      expect(extractError.status).toBe(422);
      expect(extractError.body.error).toBe("transcript_empty");
    }
  });

  it("throws ExtractError with parsed body on 502", async () => {
    server.use(
      http.post("/api/extract", () =>
        HttpResponse.json(
          { error: "llm_unavailable", detail: "upstream 503" },
          { status: 502 }
        )
      )
    );
    await expect(postExtract("x")).rejects.toMatchObject({
      status: 502,
      body: { error: "llm_unavailable" },
    });
  });
});
