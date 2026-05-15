import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders a hint to paste a transcript", () => {
    render(<EmptyState />);
    expect(screen.getByText(/paste a transcript/i)).toBeInTheDocument();
  });
});
