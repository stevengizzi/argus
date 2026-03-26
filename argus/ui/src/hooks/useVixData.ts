/**
 * TanStack Query hook for VIX regime data.
 *
 * Fetches current VIX landscape from GET /api/v1/vix/current with 60s polling.
 * Returns typed VixCurrentResponse with loading/error/disabled states.
 *
 * Sprint 27.9, Session 4.
 */

import { useQuery } from '@tanstack/react-query';
import { getVixCurrent } from '../api/client';
import type { VixCurrentResponse } from '../api/types';

export function useVixData() {
  return useQuery<VixCurrentResponse, Error>({
    queryKey: ['vix', 'current'],
    queryFn: getVixCurrent,
    refetchInterval: 60_000, // 60 seconds
  });
}
