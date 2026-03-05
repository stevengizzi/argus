/**
 * TanStack Query hooks for fetching intraday bars for a symbol.
 *
 * useSymbolBars: For the Pattern Library's symbol detail panel to display charts.
 * useTradeChartBars: For trade analysis charts with specific time ranges.
 *
 * Stale time: 30 seconds (market data updates frequently).
 */

import { useQuery } from '@tanstack/react-query';
import { fetchSymbolBars } from '../api/client';
import type { BarsResponse } from '../api/types';

export function useSymbolBars(symbol: string | null, limit: number = 390) {
  return useQuery<BarsResponse, Error>({
    queryKey: ['market', symbol, 'bars', limit],
    queryFn: () => fetchSymbolBars(symbol!, limit),
    enabled: !!symbol, // Only fetch when symbol is provided
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook for fetching bars within a specific time range.
 *
 * Used by TradeChart to fetch bars around a trade's entry/exit times.
 */
export function useTradeChartBars(
  symbol: string | null,
  startTime: string | null,
  endTime: string | null,
) {
  return useQuery<BarsResponse, Error>({
    queryKey: ['market', symbol, 'bars', 'range', startTime, endTime],
    queryFn: () => fetchSymbolBars(symbol!, undefined, startTime!, endTime!),
    enabled: !!symbol && !!startTime,
    staleTime: 30 * 1000, // 30 seconds
  });
}
