/**
 * EquityCurve component tests.
 *
 * Sprint 21d Session 9: Comparative period overlay tests.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EquityCurve } from './EquityCurve';

// Mock LWChart to avoid Lightweight Charts initialization in tests
vi.mock('../../components/LWChart', () => ({
  LWChart: ({ height }: { height: number }) => (
    <div data-testid="lw-chart" style={{ height: `${height}px` }} />
  ),
}));

// Mock the animation utility
vi.mock('../../utils/chartAnimation', () => ({
  animateChartDrawIn: vi.fn(),
}));

const mockDailyPnl = [
  { date: '2026-02-01', pnl: 100, trades: 2 },
  { date: '2026-02-02', pnl: 150, trades: 3 },
  { date: '2026-02-03', pnl: -50, trades: 1 },
  { date: '2026-02-04', pnl: 200, trades: 4 },
];

const mockComparisonData = [
  { date: '2026-01-01', pnl: 80, trades: 2 },
  { date: '2026-01-02', pnl: 120, trades: 3 },
  { date: '2026-01-03', pnl: -30, trades: 1 },
  { date: '2026-01-04', pnl: 180, trades: 4 },
];

describe('EquityCurve', () => {
  it('renders equity curve chart', () => {
    render(<EquityCurve dailyPnl={mockDailyPnl} />);

    // Should show the title
    expect(screen.getByText('Equity Curve')).toBeInTheDocument();

    // Should render the chart
    expect(screen.getByTestId('lw-chart')).toBeInTheDocument();
  });

  it('shows empty state when no data', () => {
    render(<EquityCurve dailyPnl={[]} />);

    expect(screen.getByText('Not enough data for this period')).toBeInTheDocument();
  });

  it('shows comparison toggle when showComparison is true and comparison data provided', () => {
    render(
      <EquityCurve
        dailyPnl={mockDailyPnl}
        period="month"
        showComparison={true}
        comparisonData={mockComparisonData}
      />
    );

    // Should show the comparison toggle
    expect(screen.getByText('Compare with previous month')).toBeInTheDocument();

    // Should have a checkbox
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeInTheDocument();
    expect(checkbox).not.toBeChecked();
  });

  it('hides comparison toggle when showComparison is false', () => {
    render(
      <EquityCurve
        dailyPnl={mockDailyPnl}
        period="month"
        showComparison={false}
        comparisonData={mockComparisonData}
      />
    );

    // Should NOT show the comparison toggle
    expect(screen.queryByText('Compare with previous month')).not.toBeInTheDocument();
  });

  it('hides comparison toggle when no comparison data', () => {
    render(
      <EquityCurve
        dailyPnl={mockDailyPnl}
        period="month"
        showComparison={true}
        comparisonData={undefined}
      />
    );

    // Should NOT show the comparison toggle (no comparison data)
    expect(screen.queryByText('Compare with previous month')).not.toBeInTheDocument();
  });

  it('shows legend when comparison is enabled', () => {
    render(
      <EquityCurve
        dailyPnl={mockDailyPnl}
        period="month"
        showComparison={true}
        comparisonData={mockComparisonData}
      />
    );

    // Initially no legend
    expect(screen.queryByText('Current month')).not.toBeInTheDocument();

    // Enable comparison
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);

    // Should now show legend
    expect(screen.getByText('Current month')).toBeInTheDocument();
    expect(screen.getByText('Previous month')).toBeInTheDocument();
  });

  it('calls onComparisonToggle when checkbox changes', () => {
    const mockToggle = vi.fn();

    render(
      <EquityCurve
        dailyPnl={mockDailyPnl}
        period="week"
        showComparison={true}
        comparisonData={mockComparisonData}
        onComparisonToggle={mockToggle}
      />
    );

    // Toggle the checkbox
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);

    expect(mockToggle).toHaveBeenCalledWith(true);

    // Toggle again
    fireEvent.click(checkbox);
    expect(mockToggle).toHaveBeenCalledWith(false);
  });

  it('uses correct period label for toggle text', () => {
    const { rerender } = render(
      <EquityCurve
        dailyPnl={mockDailyPnl}
        period="week"
        showComparison={true}
        comparisonData={mockComparisonData}
      />
    );

    expect(screen.getByText('Compare with previous week')).toBeInTheDocument();

    rerender(
      <EquityCurve
        dailyPnl={mockDailyPnl}
        period="month"
        showComparison={true}
        comparisonData={mockComparisonData}
      />
    );

    expect(screen.getByText('Compare with previous month')).toBeInTheDocument();

    rerender(
      <EquityCurve
        dailyPnl={mockDailyPnl}
        period="today"
        showComparison={true}
        comparisonData={mockComparisonData}
      />
    );

    expect(screen.getByText('Compare with previous day')).toBeInTheDocument();
  });

  it('applies transitioning opacity when isTransitioning is true', () => {
    const { container } = render(
      <EquityCurve dailyPnl={mockDailyPnl} isTransitioning={true} />
    );

    // The chart container should have opacity-40 class
    const transitionDiv = container.querySelector('.opacity-40');
    expect(transitionDiv).toBeInTheDocument();
  });
});
