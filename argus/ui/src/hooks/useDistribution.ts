/**
 * TanStack Query hook for R-multiple distribution data.
 *
 * Fetches histogram data showing trade outcomes in R-multiples.
 * Uses keepPreviousData to maintain stable UI during period changes.
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getDistribution } from '../api/client';
import type { DistributionResponse, PerformancePeriod } from '../api/types';

export function useDistribution(period: PerformancePeriod, strategyId?: string) {
  return useQuery<DistributionResponse, Error>({
    queryKey: ['distribution', period, { strategyId }],
    queryFn: () => getDistribution(period, strategyId),
    refetchInterval: 60_000, // 1 minute
    placeholderData: keepPreviousData,
  });
}
