/**
 * TanStack Query hook for session summary.
 *
 * Fetches today's trading session summary. Used by SessionSummaryCard.
 * 60s polling. Refetch on window focus for fresh data after returning.
 */

import { useQuery } from '@tanstack/react-query';
import { getSessionSummary } from '../api/client';
import type { SessionSummaryResponse } from '../api/types';

export function useSessionSummary(date?: string) {
  return useQuery<SessionSummaryResponse, Error>({
    queryKey: ['session-summary', date],
    queryFn: () => getSessionSummary(date),
    refetchInterval: 60_000, // 60 seconds - session data doesn't change rapidly
    refetchOnWindowFocus: true, // Refresh when user returns to tab
  });
}
