import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorAlert } from "./ErrorAlert";
import { ExtractError } from "../../api/client";

describe("ErrorAlert", () => {
  it("renders the empty-transcript message", () => {
    const err = new ExtractError(422, { error: "transcript_empty" });
    render(<ErrorAlert error={err} />);
    expect(screen.getByText(/paste a transcript/i)).toBeInTheDocument();
  });

  it("renders the too-long message with length and max from the response body", () => {
    const err = new ExtractError(422, {
      error: "transcript_too_long",
      length: 60000,
      max_length: 50000,
    });
    render(<ErrorAlert error={err} />);
    expect(screen.getByText(/too long/i)).toBeInTheDocument();
    expect(screen.getByText(/60,000/)).toBeInTheDocument();
    expect(screen.getByText(/50,000/)).toBeInTheDocument();
  });

  it("renders the extraction-failed message", () => {
    const err = new ExtractError(500, { error: "extraction_failed" });
    render(<ErrorAlert error={err} />);
    expect(screen.getByText(/unusable response/i)).toBeInTheDocument();
  });

  it("renders the llm-unavailable message", () => {
    const err = new ExtractError(502, { error: "llm_unavailable" });
    render(<ErrorAlert error={err} />);
    expect(
      screen.getByText(/extraction service is unavailable/i)
    ).toBeInTheDocument();
  });

  it("renders the llm-timeout message", () => {
    const err = new ExtractError(504, { error: "llm_timeout" });
    render(<ErrorAlert error={err} />);
    expect(screen.getByText(/timed out/i)).toBeInTheDocument();
  });

  it("renders the internal message", () => {
    const err = new ExtractError(500, { error: "internal" });
    render(<ErrorAlert error={err} />);
    expect(screen.getByText(/something went wrong on our side/i))
      .toBeInTheDocument();
  });

  it("falls back to a generic message for non-ExtractError errors", () => {
    render(<ErrorAlert error={new Error("network down")} />);
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });
});
