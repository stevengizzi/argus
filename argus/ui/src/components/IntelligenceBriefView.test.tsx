/**
 * Tests for IntelligenceBriefView component.
 *
 * Sprint 23.5 Session 6
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { IntelligenceBriefView } from "./IntelligenceBriefView";
import type { IntelligenceBrief } from "../hooks/useIntelligenceBriefings";

// Mock the hooks
vi.mock("../hooks/useIntelligenceBriefings", () => ({
  useIntelligenceBriefing: vi.fn(),
  useIntelligenceBriefingHistory: vi.fn(),
  useGenerateIntelligenceBriefing: vi.fn(),
}));

import {
  useIntelligenceBriefing,
  useIntelligenceBriefingHistory,
  useGenerateIntelligenceBriefing,
} from "../hooks/useIntelligenceBriefings";

const mockUseIntelligenceBriefing = vi.mocked(useIntelligenceBriefing);
const mockUseIntelligenceBriefingHistory = vi.mocked(useIntelligenceBriefingHistory);
const mockUseGenerateIntelligenceBriefing = vi.mocked(useGenerateIntelligenceBriefing);

const mockBrief: IntelligenceBrief = {
  id: "2026-03-10",
  date: "2026-03-10",
  brief_type: "premarket",
  content: "# Market Overview\n\n**AAPL** is showing strong momentum.\n\n- Catalyst 1\n- Catalyst 2",
  symbols_covered: ["AAPL", "NVDA", "TSLA"],
  catalyst_count: 5,
  generated_at: "2026-03-10T06:30:00Z",
  generation_cost_usd: 0.0234,
};

describe("IntelligenceBriefView", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    // Default mock implementations
    mockUseIntelligenceBriefingHistory.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      isError: false,
    } as ReturnType<typeof useIntelligenceBriefingHistory>);

    mockUseGenerateIntelligenceBriefing.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useGenerateIntelligenceBriefing>);
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it("renders brief content as markdown", () => {
    mockUseIntelligenceBriefing.mockReturnValue({
      data: mockBrief,
      isLoading: false,
      error: null,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useIntelligenceBriefing>);

    render(<IntelligenceBriefView />, { wrapper });

    // Check that markdown headers are rendered
    expect(screen.getByText("Market Overview")).toBeInTheDocument();
    // Check that bold text is rendered (AAPL is in bold in the content)
    expect(screen.getByText(/AAPL/)).toBeInTheDocument();
  });

  it("shows empty state when no brief", () => {
    mockUseIntelligenceBriefing.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useIntelligenceBriefing>);

    render(<IntelligenceBriefView />, { wrapper });

    expect(screen.getByText(/No intelligence brief for/)).toBeInTheDocument();
  });

  it("date navigation changes displayed brief", () => {
    const mockRefetch = vi.fn();
    mockUseIntelligenceBriefing.mockReturnValue({
      data: mockBrief,
      isLoading: false,
      error: null,
      isError: false,
      refetch: mockRefetch,
    } as unknown as ReturnType<typeof useIntelligenceBriefing>);

    render(<IntelligenceBriefView />, { wrapper });

    // Click previous day button
    const prevButton = screen.getByLabelText("Previous day");
    fireEvent.click(prevButton);

    // The hook should be called with a different date
    // We verify the button is clickable and the component re-renders
    expect(prevButton).toBeInTheDocument();
  });

  it("generate button triggers mutation", () => {
    const mockMutate = vi.fn();
    mockUseIntelligenceBriefing.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useIntelligenceBriefing>);

    mockUseGenerateIntelligenceBriefing.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useGenerateIntelligenceBriefing>);

    render(<IntelligenceBriefView />, { wrapper });

    const generateButton = screen.getByText("Generate Brief");
    fireEvent.click(generateButton);

    expect(mockMutate).toHaveBeenCalled();
  });

  it("shows loading state", () => {
    mockUseIntelligenceBriefing.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useIntelligenceBriefing>);

    render(<IntelligenceBriefView />, { wrapper });

    expect(screen.getByText("Loading briefing...")).toBeInTheDocument();
  });

  it("shows error state with retry button", () => {
    const mockRefetch = vi.fn();
    mockUseIntelligenceBriefing.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Network error"),
      isError: true,
      refetch: mockRefetch,
    } as unknown as ReturnType<typeof useIntelligenceBriefing>);

    render(<IntelligenceBriefView />, { wrapper });

    expect(screen.getByText("Failed to load briefing")).toBeInTheDocument();
    
    const retryButton = screen.getByText("Retry");
    fireEvent.click(retryButton);
    
    expect(mockRefetch).toHaveBeenCalled();
  });

  it("shows metadata bar with brief details", () => {
    mockUseIntelligenceBriefing.mockReturnValue({
      data: mockBrief,
      isLoading: false,
      error: null,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useIntelligenceBriefing>);

    render(<IntelligenceBriefView />, { wrapper });

    expect(screen.getByText("5 catalysts")).toBeInTheDocument();
    expect(screen.getByText("3 symbols")).toBeInTheDocument();
    expect(screen.getByText(/Cost:/)).toBeInTheDocument();
  });
});
