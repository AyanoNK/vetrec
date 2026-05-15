import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TranscriptForm } from "./TranscriptForm";

describe("TranscriptForm", () => {
  it("disables submit when transcript is empty", () => {
    render(
      <TranscriptForm onSubmit={vi.fn()} disabled={false} onClear={vi.fn()} />
    );
    expect(screen.getByRole("button", { name: /extract/i })).toBeDisabled();
  });

  it("enables submit and calls onSubmit with trimmed transcript", async () => {
    const handleSubmit = vi.fn();
    const user = userEvent.setup();
    render(
      <TranscriptForm
        onSubmit={handleSubmit}
        disabled={false}
        onClear={vi.fn()}
      />
    );
    const textarea = screen.getByRole("textbox", { name: /transcript/i });
    await user.type(textarea, "  Bella presented for wellness exam.  ");
    const submit = screen.getByRole("button", { name: /extract/i });
    await waitFor(() => expect(submit).not.toBeDisabled());
    await user.click(submit);
    await waitFor(() =>
      expect(handleSubmit).toHaveBeenCalledWith(
        "Bella presented for wellness exam."
      )
    );
  });

  it("shows an inline error when submitted empty after typing then clearing", async () => {
    const user = userEvent.setup();
    render(
      <TranscriptForm
        onSubmit={vi.fn()}
        disabled={false}
        onClear={vi.fn()}
      />
    );
    const textarea = screen.getByRole("textbox", { name: /transcript/i });
    await user.type(textarea, "x");
    await user.clear(textarea);
    await user.click(screen.getByRole("button", { name: /extract/i }));
    expect(
      await screen.findByText(/paste a transcript/i)
    ).toBeInTheDocument();
  });

  it("disables submit while parent is busy", () => {
    render(
      <TranscriptForm onSubmit={vi.fn()} disabled={true} onClear={vi.fn()} />
    );
    expect(screen.getByRole("button", { name: /extract/i })).toBeDisabled();
  });

  it("updates the character counter as the user types", async () => {
    const user = userEvent.setup();
    render(
      <TranscriptForm
        onSubmit={vi.fn()}
        disabled={false}
        onClear={vi.fn()}
      />
    );
    await user.type(
      screen.getByRole("textbox", { name: /transcript/i }),
      "abcdef"
    );
    expect(screen.getByText(/6 \/ 50,000/)).toBeInTheDocument();
  });

  it("calls onClear and resets the field when Clear is clicked", async () => {
    const handleClear = vi.fn();
    const user = userEvent.setup();
    render(
      <TranscriptForm
        onSubmit={vi.fn()}
        disabled={false}
        onClear={handleClear}
      />
    );
    const textarea = screen.getByRole(
      "textbox",
      { name: /transcript/i }
    ) as HTMLTextAreaElement;
    await user.type(textarea, "hello");
    await user.click(screen.getByRole("button", { name: /clear/i }));
    expect(handleClear).toHaveBeenCalled();
    expect(textarea.value).toBe("");
  });
});
