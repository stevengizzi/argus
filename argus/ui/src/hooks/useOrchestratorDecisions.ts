/**
 * TanStack Query hook for orchestrator decisions.
 *
 * Fetches orchestrator decision history with optional date filter.
 * 30s polling. Defaults to today's date in ET timezone.
 */

import { useQuery } from '@tanstack/react-query';
import { getOrchestratorDecisions } from '../api/client';
import type { DecisionsResponse } from '../api/types';

/**
 * Get today's date in YYYY-MM-DD format (ET timezone).
 */
function getTodayET(): string {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  return formatter.format(new Date());
}

export function useOrchestratorDecisions(date?: string) {
  const effectiveDate = date ?? getTodayET();

  return useQuery<DecisionsResponse, Error>({
    queryKey: ['orchestrator-decisions', effectiveDate],
    queryFn: () => getOrchestratorDecisions(effectiveDate),
    refetchInterval: 30_000,
  });
}
