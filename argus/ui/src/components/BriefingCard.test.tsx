/**
 * Tests for BriefingCard component.
 *
 * Sprint 23.5 Session 6
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BriefingCard } from "./BriefingCard";
import type { IntelligenceBrief } from "../hooks/useIntelligenceBriefings";

const createBrief = (overrides: Partial<IntelligenceBrief> = {}): IntelligenceBrief => ({
  id: "2026-03-10",
  date: "2026-03-10",
  brief_type: "premarket",
  content: "# Market Overview\n\nThis is a test brief content.",
  symbols_covered: ["AAPL", "NVDA", "TSLA"],
  catalyst_count: 5,
  generated_at: "2026-03-10T06:30:00Z",
  generation_cost_usd: 0.0234,
  ...overrides,
});

describe("BriefingCard", () => {
  it("renders date and catalyst count", () => {
    const brief = createBrief();
    
    render(<BriefingCard brief={brief} onClick={() => {}} />);
    
    // Should show formatted date (Mar 10)
    expect(screen.getByText("Mar 10")).toBeInTheDocument();
    // Should show catalyst count
    expect(screen.getByText("5 catalysts")).toBeInTheDocument();
  });

  it("renders symbol count", () => {
    const brief = createBrief({ symbols_covered: ["AAPL", "NVDA", "TSLA", "AMZN"] });
    
    render(<BriefingCard brief={brief} onClick={() => {}} />);
    
    expect(screen.getByText("4 symbols")).toBeInTheDocument();
  });

  it("truncates long content", () => {
    const longContent = "# Header\n\n" + "A".repeat(100);
    const brief = createBrief({ content: longContent });
    
    render(<BriefingCard brief={brief} onClick={() => {}} />);
    
    // The content should be truncated with "..."
    const preview = screen.getByText(/A+\.\.\.$/);
    expect(preview).toBeInTheDocument();
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    const brief = createBrief();
    
    render(<BriefingCard brief={brief} onClick={onClick} />);
    
    const card = screen.getByRole("button");
    fireEvent.click(card);
    
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("shows active state when isActive is true", () => {
    const brief = createBrief();
    
    const { container } = render(
      <BriefingCard brief={brief} onClick={() => {}} isActive={true} />
    );
    
    const button = container.querySelector("button");
    expect(button?.className).toContain("bg-argus-accent");
  });

  it("shows inactive state when isActive is false", () => {
    const brief = createBrief();
    
    const { container } = render(
      <BriefingCard brief={brief} onClick={() => {}} isActive={false} />
    );
    
    const button = container.querySelector("button");
    expect(button?.className).toContain("bg-argus-surface");
    expect(button?.className).not.toContain("bg-argus-accent/10");
  });

  it("handles empty content gracefully", () => {
    const brief = createBrief({ content: "" });
    
    render(<BriefingCard brief={brief} onClick={() => {}} />);
    
    // Should still render date and counts
    expect(screen.getByText("Mar 10")).toBeInTheDocument();
    expect(screen.getByText("5 catalysts")).toBeInTheDocument();
  });

  it("handles content with only markdown headers", () => {
    const brief = createBrief({ content: "# Header Only\n## Another Header" });
    
    render(<BriefingCard brief={brief} onClick={() => {}} />);
    
    // Should still render basic info even if no preview text
    expect(screen.getByText("Mar 10")).toBeInTheDocument();
  });
});
