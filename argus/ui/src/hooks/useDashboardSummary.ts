/**
 * TanStack Query hook for aggregated dashboard data.
 *
 * Sprint 21d: Fetches all dashboard data in a single API call.
 * This eliminates staggered card loading by providing one query/one loading state.
 *
 * Uses keepPreviousData to prevent skeleton flashes on refetch or tab-switch.
 * Polls at 5s to match the account data refresh rate.
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getDashboardSummary } from '../api/client';
import type { DashboardSummaryResponse } from '../api/types';

export function useDashboardSummary() {
  return useQuery<DashboardSummaryResponse, Error>({
    queryKey: ['dashboard', 'summary'],
    queryFn: getDashboardSummary,
    staleTime: 5_000,           // Data is fresh for 5 seconds
    refetchInterval: 5_000,     // Poll every 5 seconds while tab is active
    refetchOnWindowFocus: false, // Don't refetch when user tabs back
    placeholderData: keepPreviousData, // Never flash skeletons after first load
  });
}
