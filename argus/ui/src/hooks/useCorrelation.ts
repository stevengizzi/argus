/**
 * TanStack Query hook for strategy correlation matrix.
 *
 * Fetches pairwise correlation between strategy daily returns.
 * Uses keepPreviousData to maintain stable UI during period changes.
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getCorrelation } from '../api/client';
import type { CorrelationResponse, PerformancePeriod } from '../api/types';

export function useCorrelation(period: PerformancePeriod) {
  return useQuery<CorrelationResponse, Error>({
    queryKey: ['correlation', period],
    queryFn: () => getCorrelation(period),
    refetchInterval: 60_000, // 1 minute
    placeholderData: keepPreviousData,
  });
}
