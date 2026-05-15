import type { ApiError, Timeline } from "./types";

export class ExtractError extends Error {
  constructor(public status: number, public body: ApiError) {
    super(body.detail ?? body.error);
    this.name = "ExtractError";
  }
}

export async function postExtract(transcript: string): Promise<Timeline> {
  const res = await fetch("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript }),
  });
  if (!res.ok) {
    const body = (await res.json()) as ApiError;
    throw new ExtractError(res.status, body);
  }
  return (await res.json()) as Timeline;
}
