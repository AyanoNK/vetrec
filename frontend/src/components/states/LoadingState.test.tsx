import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { LoadingState } from "./LoadingState";

describe("LoadingState", () => {
  it("renders skeleton placeholders", () => {
    const { container } = render(<LoadingState />);
    expect(container.querySelectorAll(".MuiSkeleton-root").length).toBeGreaterThan(
      0
    );
  });
});
