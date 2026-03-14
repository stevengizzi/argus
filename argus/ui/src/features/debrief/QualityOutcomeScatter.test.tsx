/**
 * Tests for QualityOutcomeScatter component.
 *
 * Sprint 24 Session 11.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QualityOutcomeScatter } from './QualityOutcomeScatter';

// Mock Recharts
vi.mock('recharts', () => ({
  ScatterChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mock-scatter-chart">{children}</div>
  ),
  Scatter: ({ children, data }: { children: React.ReactNode; data: unknown[] }) => (
    <div data-testid="mock-scatter" data-points={data?.length ?? 0}>
      {children}
    </div>
  ),
  XAxis: () => <div data-testid="mock-x-axis" />,
  YAxis: () => <div data-testid="mock-y-axis" />,
  Tooltip: () => <div />,
  ReferenceLine: () => <div data-testid="mock-ref-line" />,
  Cell: ({ fill }: { fill: string }) => <div data-testid="mock-cell" data-fill={fill} />,
  Line: () => <div />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

const mockUseQualityHistory = vi.fn();
vi.mock('../../hooks/useQuality', () => ({
  useQualityHistory: () => mockUseQualityHistory(),
}));

function makeItem(
  grade: string,
  score: number,
  pnl: number | null,
  rMultiple: number | null,
  symbol = 'AAPL',
) {
  return {
    symbol,
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

describe('QualityOutcomeScatter', () => {
  it('renders scatter chart with mock data', () => {
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [
          makeItem('A+', 92, 150, 1.5),
          makeItem('B+', 70, -50, -0.5),
          makeItem('A', 85, 200, 2.0),
        ],
        total: 3,
        limit: 200,
        offset: 0,
      },
      isLoading: false,
    });

    render(<QualityOutcomeScatter />);

    expect(screen.getByTestId('quality-scatter-chart')).toBeInTheDocument();
    expect(screen.getByTestId('mock-scatter-chart')).toBeInTheDocument();
  });

  it('colors dots by grade using correct grade colors', () => {
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [
          makeItem('A+', 92, 150, 1.5),
          makeItem('C+', 55, -100, -1.0),
        ],
        total: 2,
        limit: 200,
        offset: 0,
      },
      isLoading: false,
    });

    render(<QualityOutcomeScatter />);

    const cells = screen.getAllByTestId('mock-cell');
    // A+ should be emerald (#34d399), C+ should be red (#f87171)
    const fills = cells.map((c) => c.getAttribute('data-fill'));
    expect(fills).toContain('#34d399');
    expect(fills).toContain('#f87171');
  });

  it('shows trend line label when enough data points', () => {
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [
          makeItem('A+', 92, 150, 1.5),
          makeItem('A', 85, 100, 1.0),
          makeItem('B+', 70, -50, -0.5),
        ],
        total: 3,
        limit: 200,
        offset: 0,
      },
      isLoading: false,
    });

    render(<QualityOutcomeScatter />);

    expect(screen.getByTestId('quality-scatter-trend-label')).toBeInTheDocument();
    expect(screen.getByText(/linear trend/i)).toBeInTheDocument();
  });

  it('shows empty state message when no outcomes', () => {
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [
          makeItem('A+', 92, null, null),
          makeItem('B+', 70, null, null),
        ],
        total: 2,
        limit: 200,
        offset: 0,
      },
      isLoading: false,
    });

    render(<QualityOutcomeScatter />);

    expect(screen.getByTestId('quality-scatter-empty')).toBeInTheDocument();
    expect(
      screen.getByText(/quality vs\. outcome data will appear/i),
    ).toBeInTheDocument();
  });

  it('shows empty state when no items at all', () => {
    mockUseQualityHistory.mockReturnValue({
      data: { items: [], total: 0, limit: 200, offset: 0 },
      isLoading: false,
    });

    render(<QualityOutcomeScatter />);

    expect(screen.getByTestId('quality-scatter-empty')).toBeInTheDocument();
  });

  it('shows loading skeleton', () => {
    mockUseQualityHistory.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<QualityOutcomeScatter />);

    expect(screen.getByTestId('quality-scatter-skeleton')).toBeInTheDocument();
  });

  it('filters out items without outcome_r_multiple', () => {
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [
          makeItem('A+', 92, 150, 1.5),
          makeItem('B+', 70, null, null), // no outcome — should be excluded
          makeItem('A', 85, 200, 2.0),
        ],
        total: 3,
        limit: 200,
        offset: 0,
      },
      isLoading: false,
    });

    render(<QualityOutcomeScatter />);

    // Chart should render (2 points with outcomes)
    expect(screen.getByTestId('quality-scatter-chart')).toBeInTheDocument();
    // Only 2 cells (not 3) — the null-outcome item is filtered
    const cells = screen.getAllByTestId('mock-cell');
    expect(cells).toHaveLength(2);
  });
});
