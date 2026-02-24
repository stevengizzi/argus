/**
 * TanStack Query hook for orchestrator status.
 *
 * Fetches orchestrator status including allocations, regime, and risk metrics.
 * 10s polling. Fails gracefully when orchestrator is unavailable (dev mode).
 */

import { useQuery } from '@tanstack/react-query';
import { getOrchestratorStatus } from '../api/client';
import type { OrchestratorStatusResponse } from '../api/types';

export function useOrchestratorStatus() {
  return useQuery<OrchestratorStatusResponse, Error>({
    queryKey: ['orchestrator-status'],
    queryFn: getOrchestratorStatus,
    refetchInterval: 10_000, // 10 seconds
    retry: false, // Don't retry on 503 (orchestrator unavailable)
  });
}
