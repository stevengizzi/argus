/**
 * TanStack Query hook for shadow (counterfactual) trades data.
 *
 * Fetches rejected signal positions from the CounterfactualTracker.
 * Only fetches when the tab is active — query is disabled by default and
 * enabled by the caller to avoid unnecessary requests on the Live Trades tab.
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getShadowTrades } from '../api/client';
import type { ShadowTradesResponse } from '../api/types';

export interface UseShadowTradesParams {
  strategy_id?: string;
  date_from?: string;
  date_to?: string;
  rejection_stage?: string;
  limit?: number;
  offset?: number;
}

export function useShadowTrades(params?: UseShadowTradesParams, enabled = true) {
  return useQuery<ShadowTradesResponse, Error>({
    queryKey: ['shadowTrades', params],
    queryFn: () => getShadowTrades(params),
    staleTime: 30_000,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
    placeholderData: keepPreviousData,
    enabled,
  });
}
