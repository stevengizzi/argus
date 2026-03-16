/**
 * TanStack Query hook for strategy evaluation decision events.
 *
 * Polls the strategy decisions endpoint at 3-second intervals to provide
 * a live-scrolling log of evaluation events.
 *
 * Sprint 24.5 Session 4.
 */

import { useQuery } from '@tanstack/react-query';
import { getStrategyDecisions } from '../api/client';
import type { EvaluationEvent } from '../api/types';

export type { EvaluationEvent } from '../api/types';

interface UseStrategyDecisionsOptions {
  symbol?: string;
  limit?: number;
  enabled?: boolean;
}

export function useStrategyDecisions(
  strategyId: string | null,
  options?: UseStrategyDecisionsOptions
) {
  const isEnabled = options?.enabled ?? !!strategyId;

  return useQuery<EvaluationEvent[], Error>({
    queryKey: ['strategy-decisions', strategyId, options?.symbol, options?.limit],
    queryFn: () =>
      getStrategyDecisions(strategyId!, {
        symbol: options?.symbol,
        limit: options?.limit,
      }),
    staleTime: 3_000,
    refetchInterval: 3_000,
    refetchOnWindowFocus: false,
    enabled: isEnabled,
  });
}
