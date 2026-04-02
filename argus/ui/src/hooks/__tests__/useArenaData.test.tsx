/**
 * Tests for useArenaData hook, sortPositions, and filterPositions.
 *
 * Sprint 32.75, Session 10.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { sortPositions, filterPositions, useArenaData } from '../useArenaData';
import type { ArenaPosition } from '../../api/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockFetch = vi.fn();
global.fetch = mockFetch;

vi.mock('../../api/client', async () => {
  const actual = await vi.importActual('../../api/client');
  return {
    ...actual,
    getToken: vi.fn(() => 'mock-token'),
  };
});

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makePosition(overrides: Partial<ArenaPosition> = {}): ArenaPosition {
  return {
    symbol: 'AAPL',
    strategy_id: 'strat_orb_breakout',
    side: 'long',
    shares: 100,
    entry_price: 200,
    current_price: 205,
    stop_price: 195,
    target_prices: [210, 220],
    trailing_stop_price: null,
    unrealized_pnl: 500,
    r_multiple: 1.0,
    hold_duration_seconds: 300,
    quality_grade: 'A',
    entry_time: '2026-04-01T09:30:00Z',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// sortPositions
// ---------------------------------------------------------------------------

describe('sortPositions', () => {
  it('sorts by entry_time newest first', () => {
    const positions = [
      makePosition({ symbol: 'A', entry_time: '2026-04-01T09:30:00Z' }),
      makePosition({ symbol: 'B', entry_time: '2026-04-01T10:15:00Z' }),
      makePosition({ symbol: 'C', entry_time: '2026-04-01T09:45:00Z' }),
    ];
    const result = sortPositions(positions, 'entry_time');
    expect(result.map((p) => p.symbol)).toEqual(['B', 'C', 'A']);
  });

  it('sorts by strategy alphabetically then entry_time newest first within group', () => {
    const positions = [
      makePosition({ symbol: 'X', strategy_id: 'strat_vwap', entry_time: '2026-04-01T10:00:00Z' }),
      makePosition({ symbol: 'Y', strategy_id: 'strat_orb', entry_time: '2026-04-01T09:45:00Z' }),
      makePosition({ symbol: 'Z', strategy_id: 'strat_orb', entry_time: '2026-04-01T10:05:00Z' }),
    ];
    const result = sortPositions(positions, 'strategy');
    expect(result[0].strategy_id).toBe('strat_orb');
    expect(result[1].strategy_id).toBe('strat_orb');
    // Within strat_orb: Z (10:05) before Y (09:45)
    expect(result[0].symbol).toBe('Z');
    expect(result[1].symbol).toBe('Y');
    expect(result[2].strategy_id).toBe('strat_vwap');
  });

  it('sorts by pnl highest first', () => {
    const positions = [
      makePosition({ symbol: 'A', unrealized_pnl: 100 }),
      makePosition({ symbol: 'B', unrealized_pnl: 500 }),
      makePosition({ symbol: 'C', unrealized_pnl: -50 }),
    ];
    const result = sortPositions(positions, 'pnl');
    expect(result.map((p) => p.symbol)).toEqual(['B', 'A', 'C']);
  });

  it('sorts by urgency: nearest to any exit level first', () => {
    // entry=200, stop=190, t1=210 → range=10
    // pos A: current=209 → distToStop=19, distToT1=1 → urgency = min(19,1)/10 = 0.1 (most urgent)
    // pos B: current=200 → distToStop=10, distToT1=10 → urgency = 10/10 = 1.0
    // pos C: current=195 → distToStop=5, distToT1=15 → urgency = 5/10 = 0.5
    const positions = [
      makePosition({ symbol: 'B', entry_price: 200, stop_price: 190, target_prices: [210], current_price: 200 }),
      makePosition({ symbol: 'C', entry_price: 200, stop_price: 190, target_prices: [210], current_price: 195 }),
      makePosition({ symbol: 'A', entry_price: 200, stop_price: 190, target_prices: [210], current_price: 209 }),
    ];
    const result = sortPositions(positions, 'urgency');
    expect(result.map((p) => p.symbol)).toEqual(['A', 'C', 'B']);
  });

  it('does not mutate the input array', () => {
    const positions = [
      makePosition({ symbol: 'X', unrealized_pnl: 100 }),
      makePosition({ symbol: 'Y', unrealized_pnl: 500 }),
    ];
    const original = [...positions];
    sortPositions(positions, 'pnl');
    expect(positions[0].symbol).toBe(original[0].symbol);
  });
});

// ---------------------------------------------------------------------------
// filterPositions
// ---------------------------------------------------------------------------

describe('filterPositions', () => {
  const positions = [
    makePosition({ symbol: 'A', strategy_id: 'strat_orb_breakout' }),
    makePosition({ symbol: 'B', strategy_id: 'strat_vwap_reclaim' }),
    makePosition({ symbol: 'C', strategy_id: 'strat_orb_breakout' }),
  ];

  it('returns all positions when filter is "all"', () => {
    expect(filterPositions(positions, 'all')).toHaveLength(3);
  });

  it('narrows to matching strategy', () => {
    const result = filterPositions(positions, 'strat_orb_breakout');
    expect(result).toHaveLength(2);
    expect(result.every((p) => p.strategy_id === 'strat_orb_breakout')).toBe(true);
  });

  it('returns empty array when no positions match filter', () => {
    expect(filterPositions(positions, 'strat_afternoon_momentum')).toHaveLength(0);
  });

  it('does not mutate the input array', () => {
    filterPositions(positions, 'strat_orb_breakout');
    expect(positions).toHaveLength(3);
  });

  it('matches when position strategy_id lacks strat_ prefix but filter has it', () => {
    const unprefixed = [
      makePosition({ symbol: 'A', strategy_id: 'orb_breakout' }),
      makePosition({ symbol: 'B', strategy_id: 'vwap_reclaim' }),
    ];
    const result = filterPositions(unprefixed, 'strat_orb_breakout');
    expect(result).toHaveLength(1);
    expect(result[0].symbol).toBe('A');
  });

  it('matches when both sides have strat_ prefix', () => {
    const prefixed = [
      makePosition({ symbol: 'X', strategy_id: 'strat_orb_breakout' }),
      makePosition({ symbol: 'Y', strategy_id: 'strat_vwap_reclaim' }),
    ];
    expect(filterPositions(prefixed, 'strat_orb_breakout')).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// useArenaData hook
// ---------------------------------------------------------------------------

describe('useArenaData', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  const mockPositionsResponse = {
    positions: [
      makePosition({ symbol: 'NVDA', strategy_id: 'strat_orb_breakout' }),
      makePosition({ symbol: 'TSLA', strategy_id: 'strat_vwap_reclaim' }),
    ],
    stats: { position_count: 2, total_pnl: 1000, net_r: 2.0 },
    timestamp: '2026-04-01T10:00:00Z',
  };

  const mockCandlesResponse = (symbol: string) => ({
    symbol,
    candles: [
      { time: 1700000000, open: 200, high: 205, low: 198, close: 202, volume: 1000 },
    ],
  });

  it('fetches positions and returns them', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/arena/positions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPositionsResponse),
        });
      }
      const symbol = url.includes('NVDA') ? 'NVDA' : 'TSLA';
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockCandlesResponse(symbol)),
      });
    });

    const { result } = renderHook(() => useArenaData(), { wrapper });

    await waitFor(() => {
      expect(result.current.positions).toHaveLength(2);
    });

    expect(result.current.positions[0].symbol).toBe('NVDA');
    expect(result.current.stats.total_pnl).toBe(1000);
    expect(result.current.error).toBeNull();
  });

  it('fetches candles for each position symbol', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/arena/positions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPositionsResponse),
        });
      }
      const symbol = url.includes('NVDA') ? 'NVDA' : 'TSLA';
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockCandlesResponse(symbol)),
      });
    });

    const { result } = renderHook(() => useArenaData(), { wrapper });

    await waitFor(() => {
      expect(result.current.candlesBySymbol['NVDA']).toBeDefined();
    });

    expect(result.current.candlesBySymbol['NVDA']).toHaveLength(1);
    expect(result.current.candlesBySymbol['TSLA']).toHaveLength(1);
    // CandleData strips volume — only time/open/high/low/close present
    expect(result.current.candlesBySymbol['NVDA'][0]).not.toHaveProperty('volume');
  });

  it('returns default stats and empty arrays while loading', () => {
    // Never resolves — stays in loading state
    mockFetch.mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useArenaData(), { wrapper });

    expect(result.current.positions).toHaveLength(0);
    expect(result.current.candlesBySymbol).toEqual({});
    expect(result.current.stats.position_count).toBe(0);
  });

  it('exposes error when positions fetch fails', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 });

    const { result } = renderHook(() => useArenaData(), { wrapper });

    await waitFor(() => {
      expect(result.current.error).not.toBeNull();
    });
  });
});
