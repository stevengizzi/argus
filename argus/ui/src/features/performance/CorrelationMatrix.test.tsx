/**
 * CorrelationMatrix component tests.
 *
 * Sprint 21d Session 8: Strategy correlation matrix visualization.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CorrelationMatrix } from './CorrelationMatrix';

// Mock the useCorrelation hook
vi.mock('../../hooks/useCorrelation', () => ({
  useCorrelation: vi.fn(),
}));

import { useCorrelation } from '../../hooks/useCorrelation';

const mockCorrelationData = {
  strategy_ids: [
    'strat_orb_breakout',
    'strat_orb_scalp',
    'strat_vwap_reclaim',
    'strat_afternoon_momentum',
  ],
  matrix: [
    [1.0, 0.45, 0.12, 0.08],
    [0.45, 1.0, 0.22, 0.15],
    [0.12, 0.22, 1.0, 0.28],
    [0.08, 0.15, 0.28, 1.0],
  ],
  period: 'month',
  data_days: 22,
  message: null,
  timestamp: '2026-02-28T12:00:00Z',
};

describe('CorrelationMatrix', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders NxN grid with correlation values', () => {
    vi.mocked(useCorrelation).mockReturnValue({
      data: mockCorrelationData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useCorrelation>);

    render(<CorrelationMatrix period="month" />);

    // Should show the title
    expect(screen.getByText('Correlation Matrix')).toBeInTheDocument();

    // Should show data days count
    expect(
      screen.getByText(/Pairwise strategy return correlations \(22 trading days\)/)
    ).toBeInTheDocument();

    // Should render SVG with matrix
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Should have cells (4x4 = 16 rectangles for the matrix)
    const rects = svg?.querySelectorAll('rect');
    expect(rects?.length).toBe(16);

    // Should show diagonal values (1.00)
    const diagonalTexts = screen.getAllByText('1.00');
    expect(diagonalTexts.length).toBe(4); // 4 strategies = 4 diagonal cells

    // Should show correlation values (symmetric matrix, so values appear twice)
    const correlationTexts045 = screen.getAllByText('0.45');
    expect(correlationTexts045.length).toBe(2); // Symmetric: appears at [0,1] and [1,0]

    const correlationTexts012 = screen.getAllByText('0.12');
    expect(correlationTexts012.length).toBe(2); // Symmetric: appears at [0,2] and [2,0]

    // Should show color scale legend
    expect(screen.getByText('-1.0')).toBeInTheDocument();
    expect(screen.getByText('+1.0')).toBeInTheDocument();

    // Should show interpretation helper
    expect(
      screen.getByText(/Low correlations.*indicate good diversification/)
    ).toBeInTheDocument();
  });

  it('shows empty state when insufficient data', () => {
    vi.mocked(useCorrelation).mockReturnValue({
      data: {
        strategy_ids: ['strat_orb_breakout'],
        matrix: [[1.0]],
        period: 'month',
        data_days: 3,
        message: 'Need at least 5 trading days',
        timestamp: '2026-02-28T12:00:00Z',
      },
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useCorrelation>);

    render(<CorrelationMatrix period="month" />);

    expect(
      screen.getByText('Insufficient data for correlation analysis')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Need 5+ trading days with at least 2 strategies')
    ).toBeInTheDocument();
  });

  it('shows loading state', () => {
    vi.mocked(useCorrelation).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isFetching: true,
    } as ReturnType<typeof useCorrelation>);

    const { container } = render(<CorrelationMatrix period="month" />);

    // Should show title
    expect(screen.getByText('Correlation Matrix')).toBeInTheDocument();

    // Should show skeleton grid (skeleton-shimmer class elements)
    const skeletonElements = container.querySelectorAll('.skeleton-shimmer');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it('shows error state', () => {
    vi.mocked(useCorrelation).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to fetch'),
      isFetching: false,
    } as ReturnType<typeof useCorrelation>);

    render(<CorrelationMatrix period="month" />);

    expect(screen.getByText('Failed to load correlation data')).toBeInTheDocument();
  });

  it('displays strategy single-letter abbreviations in headers', () => {
    vi.mocked(useCorrelation).mockReturnValue({
      data: mockCorrelationData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useCorrelation>);

    const { container } = render(<CorrelationMatrix period="month" />);

    // SVG text elements should contain single-letter abbreviations for headers
    const svgTextElements = container.querySelectorAll('svg text');
    const svgTextContents = Array.from(svgTextElements).map((el) => el.textContent);

    // Each letter appears twice (once in row header, once in column header)
    expect(svgTextContents.filter((t) => t === 'O').length).toBe(2);
    expect(svgTextContents.filter((t) => t === 'S').length).toBe(2);
    expect(svgTextContents.filter((t) => t === 'V').length).toBe(2);
    expect(svgTextContents.filter((t) => t === 'A').length).toBe(2);

    // Tooltips should contain full strategy names
    const titles = container.querySelectorAll('svg title');
    const titleContents = Array.from(titles).map((el) => el.textContent);
    expect(titleContents).toContain('ORB Breakout');
    expect(titleContents).toContain('ORB Scalp');
    expect(titleContents).toContain('VWAP Reclaim');
    expect(titleContents).toContain('Afternoon Momentum');
  });
});
