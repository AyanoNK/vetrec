import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TimelineView } from "./TimelineView";
import type { Timeline } from "../api/types";

describe("TimelineView", () => {
  it("renders one item per event in order", () => {
    const timeline: Timeline = {
      events: [
        {
          type: "history",
          order: 0,
          title: "First event",
          description: "first",
        },
        {
          type: "treatment",
          order: 1,
          title: "Second event",
          description: "second",
          name: "med",
          dose: null,
          route: null,
          decision: "Approved",
          progress: null,
        },
      ],
    };
    render(<TimelineView timeline={timeline} />);

    const titles = screen
      .getAllByRole("heading", { level: 3 })
      .map((h) => h.textContent);
    expect(titles).toEqual(["First event", "Second event"]);
  });

  it("renders nothing for an empty events array", () => {
    const { container } = render(
      <TimelineView timeline={{ events: [] }} />
    );
    expect(container.textContent).toBe("");
  });
});
