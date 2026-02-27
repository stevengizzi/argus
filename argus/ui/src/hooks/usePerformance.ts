/**
 * TanStack Query hook for performance data.
 *
 * Fetches performance metrics for a given period. 30s polling.
 * Uses keepPreviousData to maintain stable UI during period changes.
 *
 * Optional strategyId parameter filters metrics to a single strategy.
 * Sprint 21d: Added dateFrom/dateTo support for previous period comparison.
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getPerformance, type PerformanceQueryOptions } from '../api/client';
import type { PerformancePeriod, PerformanceResponse } from '../api/types';

export interface UsePerformanceOptions {
  /** When false, disables the query. Used when parent provides data via props. */
  enabled?: boolean;
  /** Strategy ID filter */
  strategyId?: string;
  /** Override start date (ISO format) */
  dateFrom?: string;
  /** Override end date (ISO format) */
  dateTo?: string;
}

export function usePerformance(
  period: PerformancePeriod,
  strategyIdOrOptions?: string | UsePerformanceOptions,
  options?: UsePerformanceOptions
) {
  // Handle overloaded signature: (period, strategyId?, options?) or (period, options?)
  const strategyId = typeof strategyIdOrOptions === 'string' ? strategyIdOrOptions : strategyIdOrOptions?.strategyId;
  const opts = typeof strategyIdOrOptions === 'object' ? strategyIdOrOptions : options;
  const dateFrom = opts?.dateFrom;
  const dateTo = opts?.dateTo;

  return useQuery<PerformanceResponse, Error>({
    queryKey: ['performance', period, { strategyId, dateFrom, dateTo }],
    queryFn: () => {
      const queryOptions: PerformanceQueryOptions = {};
      if (strategyId) queryOptions.strategyId = strategyId;
      if (dateFrom) queryOptions.dateFrom = dateFrom;
      if (dateTo) queryOptions.dateTo = dateTo;

      return Object.keys(queryOptions).length > 0
        ? getPerformance(period, queryOptions)
        : getPerformance(period);
    },
    staleTime: 30_000, // Data is fresh for 30 seconds
    refetchInterval: 30_000, // Poll every 30 seconds while tab is active
    refetchOnWindowFocus: false, // Don't refetch when user tabs back
    placeholderData: keepPreviousData, // Show stale data while refetching
    enabled: opts?.enabled ?? true,
  });
}

/**
 * Compute previous period date range for comparison.
 *
 * - Week: previous Monday to previous Sunday
 * - Month: previous month 1st to last day
 * - Today: yesterday
 * - All: returns null (no comparison possible)
 */
export function getPreviousPeriodDates(period: PerformancePeriod): { dateFrom: string; dateTo: string } | null {
  const today = new Date();

  switch (period) {
    case 'week': {
      // Previous week: go back to previous Monday
      const dayOfWeek = today.getDay(); // 0=Sun, 1=Mon, ...
      const daysSinceMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
      const thisMonday = new Date(today);
      thisMonday.setDate(today.getDate() - daysSinceMonday);

      const prevSunday = new Date(thisMonday);
      prevSunday.setDate(thisMonday.getDate() - 1); // Previous Sunday

      const prevMonday = new Date(prevSunday);
      prevMonday.setDate(prevSunday.getDate() - 6); // Previous Monday

      return {
        dateFrom: prevMonday.toISOString().split('T')[0],
        dateTo: prevSunday.toISOString().split('T')[0],
      };
    }

    case 'month': {
      // Previous month
      const prevMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const lastDayPrevMonth = new Date(today.getFullYear(), today.getMonth(), 0);

      return {
        dateFrom: prevMonth.toISOString().split('T')[0],
        dateTo: lastDayPrevMonth.toISOString().split('T')[0],
      };
    }

    case 'today': {
      // Yesterday
      const yesterday = new Date(today);
      yesterday.setDate(today.getDate() - 1);
      const dateStr = yesterday.toISOString().split('T')[0];
      return {
        dateFrom: dateStr,
        dateTo: dateStr,
      };
    }

    case 'all':
    default:
      // No comparison for all-time
      return null;
  }
}

/**
 * Hook to fetch previous period data for comparison overlay.
 *
 * Only enabled when comparison is requested and there's a valid previous period.
 */
export function usePreviousPeriodPerformance(
  period: PerformancePeriod,
  enabled: boolean
) {
  const dates = getPreviousPeriodDates(period);

  return usePerformance(period, {
    enabled: enabled && dates !== null,
    dateFrom: dates?.dateFrom,
    dateTo: dates?.dateTo,
  });
}
