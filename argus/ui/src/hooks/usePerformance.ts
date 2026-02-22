/**
 * TanStack Query hook for performance data.
 *
 * Fetches performance metrics for a given period. 30s polling.
 */

import { useQuery } from '@tanstack/react-query';
import { getPerformance } from '../api/client';
import type { PerformancePeriod, PerformanceResponse } from '../api/types';

export function usePerformance(period: PerformancePeriod) {
  return useQuery<PerformanceResponse, Error>({
    queryKey: ['performance', period],
    queryFn: () => getPerformance(period),
    refetchInterval: 30_000, // 30 seconds
  });
}
