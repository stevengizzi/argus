/**
 * Tests for SessionTimeline component.
 *
 * Sprint 21d Code Review — New component for dashboard 3-card row.
 * Sprint 27.65 S5 — Added tests for 7-strategy rendering and dynamic source.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionTimeline } from './SessionTimeline';

// Mock useStrategies to control dynamic strategy list
vi.mock('../../hooks/useStrategies', () => ({
  useStrategies: vi.fn(() => ({
    data: undefined,
    isLoading: true,
    isError: false,
  })),
}));

// eslint-disable-next-line @typescript-eslint/consistent-type-imports
const { useStrategies } = await import('../../hooks/useStrategies');
const mockUseStrategies = vi.mocked(useStrategies);

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

// Wrapper component for Router + Query context
const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
};

// Legacy wrapper for backward compatibility
const renderWithRouter = renderWithProviders;

describe('SessionTimeline', () => {
  it('renders Session Timeline header', () => {
    renderWithRouter(<SessionTimeline />);

    expect(screen.getByText('Session Timeline')).toBeInTheDocument();
  });

  it('renders SVG timeline', () => {
    const { container } = renderWithRouter(<SessionTimeline />);

    // Check SVG is rendered
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders time labels (9:30, 12PM, 4PM)', () => {
    renderWithRouter(<SessionTimeline />);

    expect(screen.getByText('9:30')).toBeInTheDocument();
    expect(screen.getByText('12PM')).toBeInTheDocument();
    expect(screen.getByText('4PM')).toBeInTheDocument();
  });

  it('renders strategy bars with letters', () => {
    renderWithRouter(<SessionTimeline />);

    // Strategy letters should be visible
    expect(screen.getByText('O')).toBeInTheDocument(); // ORB
    expect(screen.getByText('S')).toBeInTheDocument(); // Scalp
    expect(screen.getByText('V')).toBeInTheDocument(); // VWAP
    expect(screen.getByText('A')).toBeInTheDocument(); // Afternoon
  });

  it('renders strategy window rects in SVG', () => {
    const { container } = renderWithRouter(<SessionTimeline />);

    // Should have multiple rect elements for strategy bars
    const rects = container.querySelectorAll('svg rect');
    // At least 13: 1 background + 12 strategy bars
    expect(rects.length).toBeGreaterThanOrEqual(13);
  });

  it('renders status text based on time', () => {
    renderWithRouter(<SessionTimeline />);

    // Should have some status text (varies based on current time)
    // Could be: "Pre-market...", "Active: O, S, V", "No strategies active", "After hours..."
    const statusOptions = [
      /pre-market/i,
      /active/i,
      /no strategies active/i,
      /after hours/i,
    ];

    // At least one of these should be present
    const foundStatus = statusOptions.some((pattern) => {
      try {
        screen.getByText(pattern);
        return true;
      } catch {
        return false;
      }
    });

    expect(foundStatus).toBe(true);
  });

  it('renders all 12 strategy letters when API unavailable (fallback)', () => {
    // useStrategies returns undefined data — fallback to all strategies
    mockUseStrategies.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useStrategies>);

    renderWithProviders(<SessionTimeline />);

    // All 12 strategy letters must be present
    expect(screen.getByText('O')).toBeInTheDocument(); // ORB Breakout
    expect(screen.getByText('S')).toBeInTheDocument(); // ORB Scalp
    expect(screen.getByText('V')).toBeInTheDocument(); // VWAP Reclaim
    expect(screen.getByText('R')).toBeInTheDocument(); // Red-to-Green
    expect(screen.getByText('F')).toBeInTheDocument(); // Bull Flag
    expect(screen.getByText('T')).toBeInTheDocument(); // Flat-Top Breakout
    expect(screen.getByText('A')).toBeInTheDocument(); // Afternoon Momentum
    expect(screen.getByText('D')).toBeInTheDocument(); // Dip-and-Rip
    expect(screen.getByText('H')).toBeInTheDocument(); // HOD Break
    expect(screen.getByText('G')).toBeInTheDocument(); // Gap-and-Go
    expect(screen.getByText('X')).toBeInTheDocument(); // ABCD
    expect(screen.getByText('P')).toBeInTheDocument(); // PM High Break
  });

  it('filters to registered strategies from API (dynamic source)', () => {
    // API returns only 3 strategies
    mockUseStrategies.mockReturnValue({
      data: {
        strategies: [
          { strategy_id: 'strat_orb_breakout', name: 'ORB Breakout', version: '1', is_active: true },
          { strategy_id: 'strat_vwap_reclaim', name: 'VWAP Reclaim', version: '1', is_active: true },
          { strategy_id: 'strat_bull_flag', name: 'Bull Flag', version: '1', is_active: true },
        ],
        count: 3,
        timestamp: new Date().toISOString(),
      },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useStrategies>);

    renderWithProviders(<SessionTimeline />);

    // Only the 3 registered strategy letters should appear
    expect(screen.getByText('O')).toBeInTheDocument(); // ORB Breakout
    expect(screen.getByText('V')).toBeInTheDocument(); // VWAP Reclaim
    expect(screen.getByText('F')).toBeInTheDocument(); // Bull Flag

    // Non-registered strategies should NOT appear
    expect(screen.queryByText('S')).not.toBeInTheDocument(); // ORB Scalp
    expect(screen.queryByText('R')).not.toBeInTheDocument(); // Red-to-Green
    expect(screen.queryByText('T')).not.toBeInTheDocument(); // Flat-Top
    expect(screen.queryByText('A')).not.toBeInTheDocument(); // Afternoon
  });
});
