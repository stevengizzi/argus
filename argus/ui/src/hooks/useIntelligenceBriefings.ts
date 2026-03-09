/**
 * TanStack Query hooks for intelligence briefing data.
 *
 * Fetches and manages pre-market intelligence briefs from the API.
 * Includes mutation hook for generating new briefs.
 *
 * Sprint 23.5 Session 6
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getToken } from '../api/client';

const API_BASE = '/api/v1';

// --- Type Definitions ---

export interface IntelligenceBrief {
  id: string;
  date: string;
  brief_type: string;
  content: string;
  symbols_covered: string[];
  catalyst_count: number;
  generated_at: string;
  generation_cost_usd: number;
}

interface BriefingHistoryResponse {
  briefings: Omit<IntelligenceBrief, 'id'>[];
  count: number;
}

// --- Helper Functions ---

/**
 * Fetch wrapper with JWT authentication.
 */
async function fetchWithAuth<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: { ...headers, ...options?.headers },
  });

  if (!response.ok) {
    if (response.status === 401) {
      window.location.href = '/login';
    }
    if (response.status === 404) {
      return null as T;
    }
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Transform API response to include an id field.
 * Uses date as the unique identifier since briefs are per-date.
 */
function transformBriefing(
  apiBrief: Omit<IntelligenceBrief, 'id'> | null
): IntelligenceBrief | null {
  if (!apiBrief) return null;
  return {
    ...apiBrief,
    id: apiBrief.date,
  };
}

// --- API Functions ---

async function getIntelligenceBriefing(date?: string): Promise<IntelligenceBrief | null> {
  const endpoint = date
    ? `/premarket/briefing?date=${date}`
    : '/premarket/briefing';
  const data = await fetchWithAuth<Omit<IntelligenceBrief, 'id'> | null>(endpoint);
  return transformBriefing(data);
}

async function getIntelligenceBriefingHistory(limit: number): Promise<IntelligenceBrief[]> {
  const data = await fetchWithAuth<BriefingHistoryResponse>(
    `/premarket/briefing/history?limit=${limit}`
  );
  return data.briefings.map((b) => transformBriefing(b)!);
}

async function generateIntelligenceBriefing(): Promise<IntelligenceBrief> {
  const data = await fetchWithAuth<Omit<IntelligenceBrief, 'id'>>(
    '/premarket/briefing/generate',
    { method: 'POST' }
  );
  return transformBriefing(data)!;
}

// --- Hooks ---

/**
 * Fetch an intelligence briefing for a specific date.
 *
 * @param date - Date in YYYY-MM-DD format (defaults to today ET)
 * @returns Query result with briefing data or null if not found
 */
export function useIntelligenceBriefing(date?: string) {
  return useQuery<IntelligenceBrief | null, Error>({
    queryKey: ['intelligence-briefing', date ?? 'today'],
    queryFn: () => getIntelligenceBriefing(date),
    staleTime: Infinity, // Briefs don't change once generated
    refetchOnWindowFocus: false,
  });
}

/**
 * Fetch intelligence briefing history.
 *
 * @param limit - Maximum number of briefings to return (default 30)
 * @returns Query result with list of past briefings
 */
export function useIntelligenceBriefingHistory(limit: number = 30) {
  return useQuery<IntelligenceBrief[], Error>({
    queryKey: ['intelligence-briefings', 'history', limit],
    queryFn: () => getIntelligenceBriefingHistory(limit),
    staleTime: 60_000, // 1 minute
    refetchOnWindowFocus: false,
  });
}

/**
 * Mutation hook for generating a new intelligence briefing.
 *
 * On success, invalidates the briefing query cache.
 *
 * @returns Mutation object with mutate function and loading state
 */
export function useGenerateIntelligenceBriefing() {
  const queryClient = useQueryClient();

  return useMutation<IntelligenceBrief, Error>({
    mutationFn: generateIntelligenceBriefing,
    onSuccess: (data) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ['intelligence-briefing'] });
      queryClient.invalidateQueries({ queryKey: ['intelligence-briefings', 'history'] });
      // Also set the new briefing directly in cache
      queryClient.setQueryData(['intelligence-briefing', data.date], data);
      queryClient.setQueryData(['intelligence-briefing', 'today'], data);
    },
  });
}
