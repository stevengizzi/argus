/**
 * TanStack Query hook for goals configuration.
 *
 * Fetches the monthly target and other goal-related settings.
 * Uses long stale time since config rarely changes.
 */

import { useQuery } from '@tanstack/react-query';
import { getGoalsConfig } from '../api/client';
import type { GoalsConfig } from '../api/types';

export interface UseGoalsOptions {
  /** When false, disables the query. Used when parent provides data via props. */
  enabled?: boolean;
}

export function useGoals(options?: UseGoalsOptions) {
  return useQuery<GoalsConfig, Error>({
    queryKey: ['goals'],
    queryFn: getGoalsConfig,
    staleTime: 5 * 60 * 1000, // 5 minutes - config rarely changes
    refetchOnWindowFocus: false,
    enabled: options?.enabled ?? true,
  });
}
