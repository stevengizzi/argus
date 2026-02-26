/**
 * TanStack Query hook for trades data.
 *
 * Fetches trade history with filtering and pagination. 30s polling.
 * Uses keepPreviousData to maintain stable UI during filter changes.
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getTrades } from '../api/client';
import type { TradesResponse } from '../api/types';

export interface UseTradesParams {
  strategy_id?: string;
  symbol?: string;
  date_from?: string;
  date_to?: string;
  outcome?: 'win' | 'loss' | 'breakeven';
  limit?: number;
  offset?: number;
}

export function useTrades(params?: UseTradesParams) {
  return useQuery<TradesResponse, Error>({
    queryKey: ['trades', params],
    queryFn: () => getTrades(params),
    refetchInterval: 30_000, // 30 seconds
    placeholderData: keepPreviousData, // Keep previous data while fetching new
  });
}
