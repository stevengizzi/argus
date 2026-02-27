/**
 * TanStack Query hook for trade activity heatmap data.
 *
 * Fetches heatmap data showing trade activity by hour of day and day of week.
 * Uses keepPreviousData to maintain stable UI during period changes.
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getHeatmapData } from '../api/client';
import type { HeatmapResponse, PerformancePeriod } from '../api/types';

export function useHeatmapData(period: PerformancePeriod, strategyId?: string) {
  return useQuery<HeatmapResponse, Error>({
    queryKey: ['heatmap', period, { strategyId }],
    queryFn: () => getHeatmapData(period, strategyId),
    refetchInterval: 60_000, // 1 minute
    placeholderData: keepPreviousData,
  });
}
