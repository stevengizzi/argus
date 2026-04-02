/**
 * useArenaData: TanStack Query hook for The Arena page.
 *
 * Fetches open positions every 5 seconds and candle history per symbol
 * (cached indefinitely until the component unmounts — live updates arrive
 * via WebSocket in S11).
 *
 * Also exports pure sortPositions and filterPositions helpers used by
 * ArenaPage and tested independently.
 *
 * Sprint 32.75, Session 10.
 */

import { useQuery, useQueries } from '@tanstack/react-query';
import type { UTCTimestamp } from 'lightweight-charts';
import { getArenaPositions, getArenaCandles } from '../api/client';
import type { ArenaPosition, ArenaPositionsResponse, ArenaStats } from '../api/types';
import type { CandleData } from '../features/arena/MiniChart';
import type { ArenaSortMode } from '../features/arena/ArenaControls';

// ---------------------------------------------------------------------------
// Return type
// ---------------------------------------------------------------------------

export interface UseArenaDataResult {
  positions: ArenaPosition[];
  candlesBySymbol: Record<string, CandleData[]>;
  isLoading: boolean;
  error: Error | null;
  stats: ArenaStats;
}

const DEFAULT_STATS: ArenaStats = { position_count: 0, total_pnl: 0, net_r: 0 };

// ---------------------------------------------------------------------------
// Sort helpers
// ---------------------------------------------------------------------------

/**
 * Compute urgency score: min(dist-to-stop, dist-to-T1) / entry-to-T1 range.
 * Lower = more urgent. Returns Infinity when range is zero (degenerate).
 */
function computeUrgency(pos: ArenaPosition): number {
  const t1Price = pos.target_prices[0] ?? pos.entry_price;
  const range = Math.abs(t1Price - pos.entry_price);
  if (range < 0.0001) return Infinity;
  const distToStop = Math.abs(pos.current_price - pos.stop_price);
  const distToT1 = Math.abs(pos.current_price - t1Price);
  return Math.min(distToStop, distToT1) / range;
}

/**
 * Sort positions by the given mode. Returns a new array (does not mutate).
 */
export function sortPositions(positions: ArenaPosition[], mode: ArenaSortMode): ArenaPosition[] {
  const sorted = [...positions];
  switch (mode) {
    case 'entry_time':
      return sorted.sort(
        (a, b) => new Date(b.entry_time).getTime() - new Date(a.entry_time).getTime(),
      );
    case 'strategy':
      return sorted.sort((a, b) => {
        const stratComp = a.strategy_id.localeCompare(b.strategy_id);
        if (stratComp !== 0) return stratComp;
        return new Date(b.entry_time).getTime() - new Date(a.entry_time).getTime();
      });
    case 'pnl':
      return sorted.sort((a, b) => b.unrealized_pnl - a.unrealized_pnl);
    case 'urgency':
      return sorted.sort((a, b) => computeUrgency(a) - computeUrgency(b));
  }
}

/**
 * Filter positions by strategy. "all" returns the full array unchanged.
 * Returns a new array (does not mutate).
 */
export function filterPositions(positions: ArenaPosition[], strategyFilter: string): ArenaPosition[] {
  if (strategyFilter === 'all') return positions;
  return positions.filter((p) => p.strategy_id === strategyFilter);
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useArenaData(): UseArenaDataResult {
  const positionsQuery = useQuery<ArenaPositionsResponse, Error>({
    queryKey: ['arena', 'positions'],
    queryFn: getArenaPositions,
    refetchInterval: 5_000,
  });

  const positions = positionsQuery.data?.positions ?? [];
  const uniqueSymbols = [...new Set(positions.map((p) => p.symbol))];

  const candleQueries = useQueries({
    queries: uniqueSymbols.map((symbol) => ({
      queryKey: ['arena', 'candles', symbol],
      queryFn: () => getArenaCandles(symbol, 30),
      staleTime: Infinity,
    })),
  });

  const candlesBySymbol: Record<string, CandleData[]> = {};
  candleQueries.forEach((query, i) => {
    const symbol = uniqueSymbols[i];
    if (query.data && symbol !== undefined) {
      candlesBySymbol[symbol] = query.data.candles.map((bar) => ({
        time: bar.time as UTCTimestamp,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }));
    }
  });

  const isCandlesLoading = candleQueries.some((q) => q.isLoading);
  const isLoading = positionsQuery.isLoading || (positions.length > 0 && isCandlesLoading);
  const candleError = candleQueries.find((q) => q.error)?.error ?? null;
  const error = positionsQuery.error ?? (candleError instanceof Error ? candleError : null);

  return {
    positions,
    candlesBySymbol,
    isLoading,
    error,
    stats: positionsQuery.data?.stats ?? DEFAULT_STATS,
  };
}
