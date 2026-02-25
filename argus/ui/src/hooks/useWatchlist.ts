/**
 * TanStack Query hook for watchlist data.
 *
 * Fetches scanner watchlist with 10s polling (slower than positions since
 * watchlist updates less frequently).
 */

import { useQuery } from '@tanstack/react-query';
import { getWatchlist } from '../api/client';
import type { WatchlistResponse } from '../api/types';

export function useWatchlist() {
  return useQuery<WatchlistResponse, Error>({
    queryKey: ['watchlist'],
    queryFn: getWatchlist,
    refetchInterval: 10_000, // 10 seconds
  });
}
