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

export interface UsePerformanceOptions {
  /** When false, disables the query. Used when parent provides data via props. */
  enabled?: boolean;
}

export function usePerformance(
  period: PerformancePeriod,
  strategyIdOrOptions?: string | UsePerformanceOptions,
  options?: UsePerformanceOptions
) {
  // Handle overloaded signature: (period, strategyId?, options?) or (period, options?)
  const strategyId = typeof strategyIdOrOptions === 'string' ? strategyIdOrOptions : undefined;
  const opts = typeof strategyIdOrOptions === 'object' ? strategyIdOrOptions : options;

  return useQuery<PerformanceResponse, Error>({
    queryKey: ['performance', period, { strategyId }],
    queryFn: () => getPerformance(period, strategyId),
    staleTime: 30_000, // Data is fresh for 30 seconds
    refetchInterval: 30_000, // Poll every 30 seconds while tab is active
    refetchOnWindowFocus: false, // Don't refetch when user tabs back
    placeholderData: keepPreviousData, // Show stale data while refetching
    enabled: opts?.enabled ?? true,
  });
}
