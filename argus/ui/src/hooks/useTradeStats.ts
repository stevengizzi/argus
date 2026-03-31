/**
 * TanStack Query hook for server-side trade statistics.
 *
 * Fetches aggregate stats (total, wins, losses, win_rate, net_pnl, avg_r)
 * computed server-side from the full filtered dataset. Resolves DEF-102
 * (client-side stats computed from paginated subset).
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getTradeStats } from '../api/client';
import type { TradeStatsResponse } from '../api/types';

export interface UseTradeStatsParams {
  strategy_id?: string;
  date_from?: string;
  date_to?: string;
  outcome?: 'win' | 'loss' | 'breakeven';
}

export function useTradeStats(params?: UseTradeStatsParams) {
  return useQuery<TradeStatsResponse, Error>({
    queryKey: ['trade-stats', params],
    queryFn: () => getTradeStats(params),
    staleTime: 30_000,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
    placeholderData: keepPreviousData,
  });
}
