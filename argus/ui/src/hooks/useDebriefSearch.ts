/**
 * TanStack Query hook for debrief search.
 *
 * Searches across briefings, journal entries, and documents.
 * Only enabled when query is at least 2 characters.
 */

import { useQuery } from '@tanstack/react-query';
import { fetchDebriefSearch } from '../api/client';
import type { DebriefSearchResponse } from '../api/types';

export type SearchScope = 'all' | 'briefings' | 'journal' | 'documents';

/**
 * Search across debrief content.
 *
 * @param query - Search term (must be >= 2 chars to execute)
 * @param scope - Limit search to specific content type (default: 'all')
 */
export function useDebriefSearch(query: string, scope?: SearchScope) {
  return useQuery<DebriefSearchResponse, Error>({
    queryKey: ['debrief-search', query, scope],
    queryFn: () => fetchDebriefSearch(query, scope),
    enabled: query.length >= 2,
    staleTime: 30_000, // 30 seconds
  });
}
