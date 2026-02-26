/**
 * TanStack Query hook for fetching strategy spec markdown.
 *
 * Used by the Pattern Library page to display strategy documentation.
 * Stale time: 5 minutes (spec sheets don't change frequently).
 */

import { useQuery } from '@tanstack/react-query';
import { fetchStrategySpec } from '../api/client';
import type { StrategySpecResponse } from '../api/types';

export function useStrategySpec(strategyId: string | null) {
  return useQuery<StrategySpecResponse, Error>({
    queryKey: ['strategies', strategyId, 'spec'],
    queryFn: () => fetchStrategySpec(strategyId!),
    enabled: !!strategyId, // Only fetch when strategyId is provided
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
