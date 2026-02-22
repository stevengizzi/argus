/**
 * TanStack Query hook for health data.
 *
 * Fetches system health status with 15s polling.
 */

import { useQuery } from '@tanstack/react-query';
import { getHealth } from '../api/client';
import type { HealthResponse } from '../api/types';

export function useHealth() {
  return useQuery<HealthResponse, Error>({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 15_000, // 15 seconds
  });
}
