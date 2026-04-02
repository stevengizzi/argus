/**
 * Tests for Arena animation utilities and disconnection overlay.
 *
 * Sprint 32.75, Session 12.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { computePriorityScore } from '../../pages/ArenaPage';

// ---------------------------------------------------------------------------
// computePriorityScore
// ---------------------------------------------------------------------------

describe('computePriorityScore', () => {
  it('returns high priority (>0.7) when price is near stop', () => {
    // entry=500, stop=490, t1=510; price=491 → near stop
    const score = computePriorityScore(491, 500, 490, 510);
    expect(score).toBeGreaterThan(0.7);
  });

  it('returns high priority (>0.7) when price is near T1', () => {
    // entry=500, stop=490, t1=510; price=509 → near T1
    const score = computePriorityScore(509, 500, 490, 510);
    expect(score).toBeGreaterThan(0.7);
  });

  it('returns low priority (~0) when price is at entry (midpoint)', () => {
    // entry=500, stop=490, t1=510; price=500 → at entry, both proximities = 1
    const score = computePriorityScore(500, 500, 490, 510);
    expect(score).toBe(0);
  });

  it('returns 0 for degenerate range where entry <= stop', () => {
    expect(computePriorityScore(500, 490, 500, 510)).toBe(0);
  });

  it('returns 0 for degenerate range where t1 <= entry', () => {
    expect(computePriorityScore(500, 500, 490, 500)).toBe(0);
  });

  it('clamps to valid range — price below stop still returns priority in [0,1]', () => {
    // price=480 below stop=490; proximity_to_stop is negative → clamped to 0 → priority = 1
    const score = computePriorityScore(480, 500, 490, 510);
    expect(score).toBeGreaterThanOrEqual(0);
    expect(score).toBeLessThanOrEqual(1);
  });

  it('clamps to valid range — price above T1 still returns priority in [0,1]', () => {
    // price=520 above t1=510; proximity_to_T1 is negative → clamped to 0 → priority = 1
    const score = computePriorityScore(520, 500, 490, 510);
    expect(score).toBeGreaterThanOrEqual(0);
    expect(score).toBeLessThanOrEqual(1);
  });

  it('span 2 threshold: score > 0.7 maps to span 2', () => {
    const score = computePriorityScore(491, 500, 490, 510);
    expect(score > 0.7 ? 2 : 1).toBe(2);
  });

  it('span 1 threshold: score at entry (0.0) maps to span 1', () => {
    const score = computePriorityScore(500, 500, 490, 510);
    expect(score > 0.7 ? 2 : 1).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// Disconnection overlay via ArenaPage
// ---------------------------------------------------------------------------

// Mock heavy dependencies so we can render ArenaPage in isolation.
vi.mock('../../hooks/useArenaData', () => ({
  useArenaData: () => ({ positions: [], candlesBySymbol: {}, isLoading: false }),
  sortPositions: (p: unknown[]) => p,
  filterPositions: (p: unknown[]) => p,
}));

vi.mock('./MiniChart', () => ({
  MiniChart: vi.fn(() => <div data-testid="mini-chart-container" />),
}));

vi.mock('./useArenaWebSocket', () => ({
  useArenaWebSocket: vi.fn(),
}));

import { useArenaWebSocket } from './useArenaWebSocket';
import { ArenaPage } from '../../pages/ArenaPage';

const DEFAULT_HOOK_RESULT = {
  positions: [],
  stats: { position_count: 0, total_pnl: 0, net_r: 0, entries_5m: 0, exits_5m: 0 },
  liveOverlays: {},
  wsStatus: 'connected' as const,
  registerChartRef: vi.fn(),
};

describe('ArenaPage disconnection overlay', () => {
  it('does not show overlay when WS is connected', () => {
    vi.mocked(useArenaWebSocket).mockReturnValue({ ...DEFAULT_HOOK_RESULT, wsStatus: 'connected' });
    render(<ArenaPage />);
    expect(screen.queryByTestId('arena-disconnect-overlay')).not.toBeInTheDocument();
  });

  it('shows overlay when WS status is disconnected', () => {
    vi.mocked(useArenaWebSocket).mockReturnValue({
      ...DEFAULT_HOOK_RESULT,
      wsStatus: 'disconnected',
    });
    render(<ArenaPage />);
    expect(screen.getByTestId('arena-disconnect-overlay')).toBeInTheDocument();
    expect(screen.getByText(/connection lost/i)).toBeInTheDocument();
  });

  it('shows overlay when WS status is error', () => {
    vi.mocked(useArenaWebSocket).mockReturnValue({
      ...DEFAULT_HOOK_RESULT,
      wsStatus: 'error',
    });
    render(<ArenaPage />);
    expect(screen.getByTestId('arena-disconnect-overlay')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// AnimatePresence wrapper presence
// ---------------------------------------------------------------------------

describe('ArenaPage animation wrappers', () => {
  it('renders arena-card-wrapper motion divs for each position', () => {
    const positions = [
      {
        symbol: 'NVDA',
        strategy_id: 'orb_breakout',
        side: 'long' as const,
        shares: 50,
        entry_price: 500,
        current_price: 505,
        stop_price: 490,
        target_prices: [515, 530],
        trailing_stop_price: null,
        unrealized_pnl: 250,
        r_multiple: 1.0,
        hold_duration_seconds: 120,
        quality_grade: 'A',
        entry_time: '2024-01-15T09:30:00Z',
      },
    ];
    vi.mocked(useArenaWebSocket).mockReturnValue({
      ...DEFAULT_HOOK_RESULT,
      positions,
      wsStatus: 'connected',
    });
    render(<ArenaPage />);
    const wrappers = screen.getAllByTestId('arena-card-wrapper');
    expect(wrappers).toHaveLength(1);
  });
});
