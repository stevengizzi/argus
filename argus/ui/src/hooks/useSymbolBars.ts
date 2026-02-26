/**
 * TanStack Query hook for fetching intraday bars for a symbol.
 *
 * Used by the Pattern Library's symbol detail panel to display charts.
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
