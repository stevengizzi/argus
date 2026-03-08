/**
 * TanStack Query hook for universe status data.
 *
 * Fetches universe manager status with 60s polling (universe data changes
 * at most once per day, but freshness indicator is useful).
 *
 * Sprint 23: NLP Catalyst + Universe Manager
 */

import { useQuery } from '@tanstack/react-query';
import { getUniverseStatus } from '../api/client';
import type { UniverseStatusResponse } from '../api/types';

export function useUniverseStatus() {
  return useQuery<UniverseStatusResponse, Error>({
    queryKey: ['universe-status'],
    queryFn: getUniverseStatus,
    refetchInterval: 60_000, // 60 seconds
  });
}
