/**
 * TanStack Query mutations for orchestrator control operations.
 *
 * Provides mutations for:
 * - Force rebalancing allocations
 * - Overriding strategy throttle
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { triggerRebalance, overrideThrottle } from '../api/client';
import type { ThrottleOverrideRequest } from '../api/types';

/**
 * Hook to trigger orchestrator rebalance.
 */
export function useRebalanceMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: triggerRebalance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orchestrator-status'] });
      queryClient.invalidateQueries({ queryKey: ['orchestrator-decisions'] });
    },
  });
}

/**
 * Hook to override throttle for a strategy.
 */
export function useThrottleOverrideMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      strategyId,
      body,
    }: {
      strategyId: string;
      body: ThrottleOverrideRequest;
    }) => overrideThrottle(strategyId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orchestrator-status'] });
      queryClient.invalidateQueries({ queryKey: ['orchestrator-decisions'] });
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}
