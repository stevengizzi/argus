/**
 * Prefetch hook for Dashboard data.
 *
 * Prefetches slower queries (performance, trades, goals) on app startup
 * so Dashboard cards load instantly instead of showing skeleton states.
 *
 * Called in App.tsx on mount.
 */

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getPerformance, getTrades, getGoalsConfig } from '../api/client';

export function usePrefetchDashboard() {
  const queryClient = useQueryClient();

  useEffect(() => {
    // Prefetch performance data for both periods
    queryClient.prefetchQuery({
      queryKey: ['performance', 'day', { strategyId: undefined }],
      queryFn: () => getPerformance('day'),
      staleTime: 30_000,
    });

    queryClient.prefetchQuery({
      queryKey: ['performance', 'month', { strategyId: undefined }],
      queryFn: () => getPerformance('month'),
      staleTime: 30_000,
    });

    // Prefetch trades for TodayStats
    queryClient.prefetchQuery({
      queryKey: ['trades', { limit: 100 }],
      queryFn: () => getTrades({ limit: 100 }),
      staleTime: 30_000,
    });

    // Prefetch goals config
    queryClient.prefetchQuery({
      queryKey: ['goals'],
      queryFn: getGoalsConfig,
      staleTime: 5 * 60 * 1000, // 5 minutes
    });
  }, [queryClient]);
}
