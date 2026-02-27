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

export interface UseTradesOptions {
  /** When false, disables the query. Used when parent provides data via props. */
  enabled?: boolean;
}

export function useTrades(params?: UseTradesParams, options?: UseTradesOptions) {
  return useQuery<TradesResponse, Error>({
    queryKey: ['trades', params],
    queryFn: () => getTrades(params),
    staleTime: 30_000, // Data is fresh for 30 seconds
    refetchInterval: 30_000, // Poll every 30 seconds while tab is active
    refetchOnWindowFocus: false, // Don't refetch when user tabs back
    placeholderData: keepPreviousData, // Show stale data while refetching
    enabled: options?.enabled ?? true,
  });
}
