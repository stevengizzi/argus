/**
 * TanStack Query hook for fetching trades filtered by symbol.
 *
 * Used by the Pattern Library's symbol detail panel to display trade history
 * for a specific symbol. 30s polling to catch new trades.
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getTrades } from '../api/client';
import type { TradesResponse } from '../api/types';

export function useSymbolTrades(symbol: string | null) {
  return useQuery<TradesResponse, Error>({
    queryKey: ['trades', { symbol }],
    queryFn: async () => {
      // The trades endpoint currently doesn't support symbol filtering,
      // so we fetch all trades and filter client-side
      const response = await getTrades({ limit: 100 });
      const filteredTrades = response.trades.filter(
        (trade) => trade.symbol === symbol
      );
      return {
        ...response,
        trades: filteredTrades,
        total_count: filteredTrades.length,
      };
    },
    enabled: !!symbol, // Only fetch when symbol is provided
    refetchInterval: 30_000, // 30 seconds
    placeholderData: keepPreviousData,
  });
}
