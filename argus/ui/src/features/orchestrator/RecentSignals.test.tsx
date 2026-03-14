/**
 * Tests for RecentSignals component.
 *
 * Sprint 24 Session 10.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RecentSignals } from './RecentSignals';
import type { QualityScoreResponse } from '../../api/types';

const mockUseQualityHistory = vi.fn();
vi.mock('../../hooks/useQuality', () => ({
  useQualityHistory: (filters: unknown) => mockUseQualityHistory(filters),
}));

function makeSignal(overrides: Partial<QualityScoreResponse> = {}): QualityScoreResponse {
  return {
    symbol: 'AAPL',
    strategy_id: 'strat_orb_breakout',
    score: 82.5,
    grade: 'A',
    risk_tier: 'low',
    components: { ps: 85, cq: 70, vp: 90, hm: 80, ra: 88 },
    scored_at: '2026-03-14T10:15:00-04:00',
    ...overrides,
  };
}

describe('RecentSignals', () => {
  it('renders signal rows with badges', () => {
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [
          makeSignal({ symbol: 'AAPL', grade: 'A+' }),
          makeSignal({ symbol: 'NVDA', grade: 'B+', strategy_id: 'strat_vwap_reclaim' }),
          makeSignal({ symbol: 'TSLA', grade: 'B', strategy_id: 'strat_orb_scalp' }),
        ],
        total: 3,
        limit: 10,
        offset: 0,
      },
      isLoading: false,
    });

    render(<RecentSignals />);

    const list = screen.getByTestId('recent-signals-list');
    expect(list).toBeInTheDocument();

    const rows = screen.getAllByTestId('recent-signal-row');
    expect(rows).toHaveLength(3);

    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('NVDA')).toBeInTheDocument();
    expect(screen.getByText('TSLA')).toBeInTheDocument();
  });

  it('shows strategy short names', () => {
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [
          makeSignal({ strategy_id: 'strat_orb_breakout' }),
          makeSignal({ symbol: 'MSFT', strategy_id: 'strat_vwap_reclaim' }),
        ],
        total: 2,
        limit: 10,
        offset: 0,
      },
      isLoading: false,
    });

    render(<RecentSignals />);

    expect(screen.getByText('ORB')).toBeInTheDocument();
    expect(screen.getByText('VWAP')).toBeInTheDocument();
  });

  it('renders quality badges with grades', () => {
    mockUseQualityHistory.mockReturnValue({
      data: {
        items: [makeSignal({ grade: 'A+' })],
        total: 1,
        limit: 10,
        offset: 0,
      },
      isLoading: false,
    });

    render(<RecentSignals />);

    expect(screen.getByText('A+')).toBeInTheDocument();
  });

  it('shows empty state message', () => {
    mockUseQualityHistory.mockReturnValue({
      data: { items: [], total: 0, limit: 10, offset: 0 },
      isLoading: false,
    });

    render(<RecentSignals />);

    expect(screen.getByTestId('recent-signals-empty')).toBeInTheDocument();
    expect(screen.getByText('No recent signals')).toBeInTheDocument();
  });

  it('shows empty state when data is null', () => {
    mockUseQualityHistory.mockReturnValue({
      data: null,
      isLoading: false,
    });

    render(<RecentSignals />);

    expect(screen.getByText('No recent signals')).toBeInTheDocument();
  });

  it('shows loading skeleton', () => {
    mockUseQualityHistory.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    const { container } = render(<RecentSignals />);

    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('passes limit 10 to useQualityHistory', () => {
    mockUseQualityHistory.mockReturnValue({
      data: { items: [], total: 0, limit: 10, offset: 0 },
      isLoading: false,
    });

    render(<RecentSignals />);

    expect(mockUseQualityHistory).toHaveBeenCalledWith({ limit: 10 });
  });
});
