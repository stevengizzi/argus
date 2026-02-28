/**
 * RMultipleHistogram component tests.
 *
 * Sprint 21d Session 7: R-multiple distribution histogram.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RMultipleHistogram } from './RMultipleHistogram';

// Mock the useDistribution hook
vi.mock('../../hooks/useDistribution', () => ({
  useDistribution: vi.fn(),
}));

// Mock Recharts components (they don't render well in jsdom)
vi.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ReferenceLine: ({ x, stroke }: { x?: string; stroke?: string }) => (
    <div data-testid="reference-line" data-x={x} data-stroke={stroke} />
  ),
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Cell: () => <div data-testid="cell" />,
}));

import { useDistribution } from '../../hooks/useDistribution';

const mockDistributionData = {
  bins: [
    { range_min: -1.0, range_max: -0.75, count: 5, avg_pnl: -250 },
    { range_min: -0.75, range_max: -0.5, count: 8, avg_pnl: -175 },
    { range_min: -0.5, range_max: -0.25, count: 12, avg_pnl: -100 },
    { range_min: 0, range_max: 0.25, count: 15, avg_pnl: 50 },
    { range_min: 0.25, range_max: 0.5, count: 20, avg_pnl: 150 },
    { range_min: 0.5, range_max: 0.75, count: 10, avg_pnl: 300 },
    { range_min: 1.0, range_max: 1.25, count: 5, avg_pnl: 500 },
  ],
  total_trades: 75,
  mean_r: 0.45,
  median_r: 0.22,
  period: 'month',
  timestamp: '2026-02-28T12:00:00Z',
};

describe('RMultipleHistogram', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders bars with data', () => {
    vi.mocked(useDistribution).mockReturnValue({
      data: mockDistributionData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useDistribution>);

    render(<RMultipleHistogram period="month" />);

    // Should show the title
    expect(screen.getByText('R-Multiple Distribution')).toBeInTheDocument();

    // Should render the chart
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();

    // Should show mean/median annotation
    expect(screen.getByText(/Mean:/)).toBeInTheDocument();
    expect(screen.getByText(/Median:/)).toBeInTheDocument();
  });

  it('shows strategy filter dropdown', () => {
    vi.mocked(useDistribution).mockReturnValue({
      data: mockDistributionData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useDistribution>);

    render(<RMultipleHistogram period="month" />);

    // Should show strategy filter
    const select = screen.getByRole('combobox', { name: /filter by strategy/i });
    expect(select).toBeInTheDocument();

    // Should have "All Strategies" selected by default
    expect(select).toHaveValue('all');

    // Change the filter
    fireEvent.change(select, { target: { value: 'strat_orb_breakout' } });
    expect(select).toHaveValue('strat_orb_breakout');
  });

  it('shows empty state when no trades', () => {
    vi.mocked(useDistribution).mockReturnValue({
      data: { bins: [], total_trades: 0, mean_r: 0, median_r: 0, period: 'month', timestamp: '' },
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useDistribution>);

    render(<RMultipleHistogram period="month" />);

    expect(screen.getByText('No trades to analyze')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    vi.mocked(useDistribution).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isFetching: true,
    } as ReturnType<typeof useDistribution>);

    const { container } = render(<RMultipleHistogram period="month" />);

    // Should show title
    expect(screen.getByText('R-Multiple Distribution')).toBeInTheDocument();

    // Should show skeleton bars (skeleton-shimmer class elements)
    const skeletonElements = container.querySelectorAll('.skeleton-shimmer');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it('shows error state', () => {
    vi.mocked(useDistribution).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to fetch'),
      isFetching: false,
    } as ReturnType<typeof useDistribution>);

    render(<RMultipleHistogram period="month" />);

    expect(screen.getByText('Failed to load distribution data')).toBeInTheDocument();
  });
});
