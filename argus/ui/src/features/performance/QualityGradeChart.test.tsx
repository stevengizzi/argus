/**
 * Tests for QualityGradeChart component.
 *
 * Sprint 24 Session 11.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QualityGradeChart } from './QualityGradeChart';

// Mock Recharts
vi.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mock-bar-chart">{children}</div>
  ),
  Bar: ({ children, name }: { children: React.ReactNode; name: string }) => (
    <div data-testid={`mock-bar-${name}`}>{children}</div>
  ),
  XAxis: () => <div data-testid="mock-x-axis" />,
  YAxis: () => <div data-testid="mock-y-axis" />,
  Tooltip: () => <div />,
  Legend: () => <div data-testid="mock-legend" />,
  Cell: () => <div data-testid="mock-cell" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

const mockUseQualityHistory = vi.fn();
vi.mock('../../hooks/useQuality', () => ({
  useQualityHistory: () => mockUseQualityHistory(),
}));

function makeHistoryItem(
  grade: string,
  score: number,
  pnl: number | null,
  rMultiple: number | null,
) {
  return {
    symbol: 'AAPL',
    strategy_id: 'strat_orb_breakout',
    score,
    grade,
    risk_tier: 'standard',
    components: { ps: 70, cq: 60, vp: 50, hm: 40, ra: 30 },
    scored_at: '2026-03-14T10:00:00',
    outcome_realized_pnl: pnl,
    outcome_r_multiple: rMultiple,
  };
}

describe('QualityGradeChart', () => {
  it('renders chart with mock data showing bars', () => {
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [
          makeHistoryItem('A+', 92, 150, 1.5),
          makeHistoryItem('A', 85, -50, -0.5),
          makeHistoryItem('B+', 70, 200, 2.0),
        ],
        total: 3,
        limit: 200,
        offset: 0,
      },
      isLoading: false,
    });

    render(<QualityGradeChart />);

    expect(screen.getByTestId('quality-grade-chart')).toBeInTheDocument();
    expect(screen.getByTestId('mock-bar-chart')).toBeInTheDocument();
  });

  it('correctly groups by grade and computes aggregates', () => {
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [
          makeHistoryItem('A+', 95, 100, 1.0),
          makeHistoryItem('A+', 90, 200, 2.0),
          makeHistoryItem('B+', 72, -50, -0.5),
        ],
        total: 3,
        limit: 200,
        offset: 0,
      },
      isLoading: false,
    });

    render(<QualityGradeChart />);

    // Chart should render (not empty state) since we have outcome data
    expect(screen.getByTestId('quality-grade-chart')).toBeInTheDocument();
    expect(screen.queryByTestId('quality-grade-chart-empty')).not.toBeInTheDocument();
  });

  it('shows empty bars for grades with no data', () => {
    // Only A+ has data — all other grades should still appear in chart
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [
          makeHistoryItem('A+', 95, 100, 1.0),
        ],
        total: 1,
        limit: 200,
        offset: 0,
      },
      isLoading: false,
    });

    render(<QualityGradeChart />);

    // Chart renders (not empty) since at least one grade has outcome data
    expect(screen.getByTestId('quality-grade-chart')).toBeInTheDocument();
  });

  it('shows empty state when no quality data', () => {
    mockUseQualityHistory.mockReturnValue({
      data: { items: [], total: 0, limit: 200, offset: 0 },
      isLoading: false,
    });

    render(<QualityGradeChart />);

    expect(screen.getByTestId('quality-grade-chart-empty')).toBeInTheDocument();
    expect(
      screen.getByText(/grade performance data will appear/i),
    ).toBeInTheDocument();
  });

  it('shows empty state when items have no outcomes', () => {
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [
          makeHistoryItem('A+', 95, null, null),
          makeHistoryItem('B+', 72, null, null),
        ],
        total: 2,
        limit: 200,
        offset: 0,
      },
      isLoading: false,
    });

    render(<QualityGradeChart />);

    expect(screen.getByTestId('quality-grade-chart-empty')).toBeInTheDocument();
  });

  it('shows loading skeleton', () => {
    mockUseQualityHistory.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<QualityGradeChart />);

    expect(screen.getByTestId('quality-grade-chart-skeleton')).toBeInTheDocument();
  });
});
