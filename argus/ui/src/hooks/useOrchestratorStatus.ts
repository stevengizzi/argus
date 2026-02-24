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
    refetchInterval: (query) => {
      // Don't poll aggressively when orchestrator is unavailable
      if (query.state.status === 'error') return 60_000; // Check once per minute
      return 10_000; // Normal 10s polling when healthy
    },
    retry: false, // Don't retry on 503 (orchestrator unavailable)
  });
}
