/**
 * TanStack Query hook for strategies data.
 *
 * Fetches strategy info with 30s polling.
 */

import { useQuery } from '@tanstack/react-query';
import { getStrategies } from '../api/client';
import type { StrategiesResponse } from '../api/types';

export function useStrategies() {
  return useQuery<StrategiesResponse, Error>({
    queryKey: ['strategies'],
    queryFn: getStrategies,
    refetchInterval: 30_000, // 30 seconds
  });
}
