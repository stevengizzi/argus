/**
 * TanStack Query hook for positions data.
 *
 * Fetches open positions with 5s polling. Optionally filters by strategy_id.
 */

import { useQuery } from '@tanstack/react-query';
import { getPositions } from '../api/client';
import type { PositionsResponse } from '../api/types';

interface UsePositionsParams {
  strategy_id?: string;
}

export function usePositions(params?: UsePositionsParams) {
  return useQuery<PositionsResponse, Error>({
    queryKey: ['positions', params?.strategy_id],
    queryFn: () => getPositions(params),
    refetchInterval: 5_000, // 5 seconds
  });
}
