import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EventCard } from "./EventCard";
import type {
  DiagnosticEvent,
  HistoryEvent,
  PhysicalExamEvent,
  RecommendationEvent,
  TreatmentEvent,
  VitalsEvent,
} from "../api/types";

describe("EventCard", () => {
  it("renders title and description for HistoryEvent", () => {
    const event: HistoryEvent = {
      type: "history",
      order: 0,
      title: "Presenting complaint",
      description: "Vomiting for two days.",
    };
    render(<EventCard event={event} />);
    expect(screen.getByText("Presenting complaint")).toBeInTheDocument();
    expect(screen.getByText("Vomiting for two days.")).toBeInTheDocument();
  });

  it("renders findings_by_system for PhysicalExamEvent when present", () => {
    const event: PhysicalExamEvent = {
      type: "physical_exam",
      order: 1,
      title: "PE findings",
      description: "Examined.",
      findings_by_system: "Cardio: regular rhythm; GI: tense abdomen",
    };
    render(<EventCard event={event} />);
    expect(
      screen.getByText("Cardio: regular rhythm; GI: tense abdomen")
    ).toBeInTheDocument();
  });

  it("omits findings_by_system for PhysicalExamEvent when null", () => {
    const event: PhysicalExamEvent = {
      type: "physical_exam",
      order: 1,
      title: "PE findings",
      description: "Examined.",
      findings_by_system: null,
    };
    const { container } = render(<EventCard event={event} />);
    expect(container.textContent).not.toContain("null");
  });

  it("renders non-null vitals fields and omits null ones", () => {
    const event: VitalsEvent = {
      type: "vitals",
      order: 2,
      title: "Vitals",
      description: "Vital signs.",
      temperature_f: 101.4,
      heart_rate_bpm: 84,
      respiratory_rate: null,
      weight_kg: null,
      mucous_membranes: null,
      capillary_refill_seconds: null,
    };
    const { container } = render(<EventCard event={event} />);
    expect(container.textContent).toMatch(/101\.4/);
    expect(container.textContent).toMatch(/84/);
    expect(container.textContent).not.toContain("null");
  });

  it("renders DiagnosticEvent with decision chip", () => {
    const event: DiagnosticEvent = {
      type: "diagnostic",
      order: 3,
      title: "CBC ordered",
      description: "Bloodwork.",
      test_name: "CBC",
      indication: null,
      decision: "Declined",
      result: null,
    };
    render(<EventCard event={event} />);
    expect(screen.getByText("CBC")).toBeInTheDocument();
    expect(screen.getByText("Declined")).toBeInTheDocument();
  });

  it("renders TreatmentEvent with dose, decision, and progress", () => {
    const event: TreatmentEvent = {
      type: "treatment",
      order: 4,
      title: "Maropitant administered",
      description: "Anti-emetic.",
      name: "maropitant",
      dose: "1 mg/kg",
      route: "subq",
      decision: "Approved",
      progress: "Completed",
    };
    render(<EventCard event={event} />);
    expect(screen.getByText(/maropitant/)).toBeInTheDocument();
    expect(screen.getByText("Approved")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText(/1 mg\/kg/)).toBeInTheDocument();
  });

  it("renders RecommendationEvent with category", () => {
    const event: RecommendationEvent = {
      type: "recommendation",
      order: 5,
      title: "Recheck in one year",
      description: "Annual recheck.",
      category: "FollowUp",
      specifics: "in one year",
    };
    render(<EventCard event={event} />);
    expect(screen.getByText("FollowUp")).toBeInTheDocument();
    expect(screen.getAllByText(/in one year/).length).toBeGreaterThan(0);
  });
});
