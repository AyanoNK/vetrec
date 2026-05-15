import { describe, expect, it } from "vitest";
import { EVENT_STYLES } from "./eventStyling";
import type { TimelineEvent } from "../api/types";

describe("EVENT_STYLES", () => {
  it("has an entry for every TimelineEvent type", () => {
    const expectedTypes: TimelineEvent["type"][] = [
      "history",
      "physical_exam",
      "vitals",
      "diagnostic",
      "treatment",
      "recommendation",
    ];
    for (const type of expectedTypes) {
      expect(EVENT_STYLES[type]).toBeDefined();
      expect(EVENT_STYLES[type].color).toMatch(
        /^(primary|secondary|success|info|warning|error)$/
      );
      expect(EVENT_STYLES[type].icon).toBeTypeOf("string");
      expect(EVENT_STYLES[type].label.length).toBeGreaterThan(0);
    }
  });
});
