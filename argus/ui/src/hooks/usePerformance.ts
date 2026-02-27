/**
 * TanStack Query hook for performance data.
 *
 * Fetches performance metrics for a given period. 30s polling.
 * Uses keepPreviousData to maintain stable UI during period changes.
 *
 * Optional strategyId parameter filters metrics to a single strategy.
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getPerformance } from '../api/client';
import type { PerformancePeriod, PerformanceResponse } from '../api/types';

export function usePerformance(period: PerformancePeriod, strategyId?: string) {
  return useQuery<PerformanceResponse, Error>({
    queryKey: ['performance', period, { strategyId }],
    queryFn: () => getPerformance(period, strategyId),
    staleTime: 30_000, // Data is fresh for 30 seconds
    refetchInterval: 30_000, // Poll every 30 seconds while tab is active
    refetchOnWindowFocus: false, // Don't refetch when user tabs back
    placeholderData: keepPreviousData, // Show stale data while refetching
  });
}
