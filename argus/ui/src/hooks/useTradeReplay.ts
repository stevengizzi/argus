/**
 * TanStack Query hook for trade replay data.
 *
 * Fetches historical bars and trade metadata for replaying a trade.
 * Only fetches when tradeId is provided.
 */

import { useQuery } from '@tanstack/react-query';
import { getTradeReplay } from '../api/client';
import type { TradeReplayResponse } from '../api/types';

export function useTradeReplay(tradeId: string | null) {
  return useQuery<TradeReplayResponse, Error>({
    queryKey: ['tradeReplay', tradeId],
    queryFn: () => getTradeReplay(tradeId!),
    enabled: !!tradeId, // Only fetch when tradeId is provided
    staleTime: 5 * 60 * 1000, // 5 minutes - replay data doesn't change
  });
}
