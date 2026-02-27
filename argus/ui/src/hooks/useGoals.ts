/**
 * TanStack Query hook for goals configuration.
 *
 * Fetches the monthly target and other goal-related settings.
 * Uses long stale time since config rarely changes.
 */

import { useQuery } from '@tanstack/react-query';
import { getGoalsConfig } from '../api/client';
import type { GoalsConfig } from '../api/types';

export function useGoals() {
  return useQuery<GoalsConfig, Error>({
    queryKey: ['goals'],
    queryFn: getGoalsConfig,
    staleTime: 5 * 60 * 1000, // 5 minutes - config rarely changes
    refetchOnWindowFocus: false,
  });
}
