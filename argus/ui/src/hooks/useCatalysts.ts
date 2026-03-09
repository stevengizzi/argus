/**
 * TanStack Query hooks for catalyst data.
 *
 * Fetches catalyst data from the intelligence API endpoints.
 * Includes market-hours-aware refetch intervals.
 *
 * Sprint 23.5 Session 5
 */

import { useQuery } from '@tanstack/react-query';
import { getToken } from '../api/client';

const API_BASE = '/api/v1';

// --- Type Definitions ---

export interface CatalystItem {
  symbol: string;
  catalyst_type: string;  // Maps from API's 'category' field
  quality_score: number;
  headline: string;
  summary: string;
  source: string;
  source_url: string | null;
  filing_type: string | null;
  published_at: string;
  classified_at: string;
}

export interface CatalystsResponse {
  catalysts: CatalystItem[];
  count: number;
  symbol?: string;
  total?: number;
}

// --- Helper Functions ---

/**
 * Check if current time is within market hours (9:30 AM - 4:00 PM ET).
 * Used to determine refetch intervals.
 */
function isMarketHours(): boolean {
  const now = new Date();
  // Convert to ET by creating a formatter
  const etTime = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: 'numeric',
    hour12: false,
  }).format(now);

  const [hourStr, minuteStr] = etTime.split(':');
  const hour = parseInt(hourStr, 10);
  const minute = parseInt(minuteStr, 10);
  const timeInMinutes = hour * 60 + minute;

  // Market hours: 9:30 AM (570 min) to 4:00 PM (960 min) ET
  // Include some buffer for pre-market (6:00 AM - 4:30 PM)
  const preMarketStart = 6 * 60; // 6:00 AM
  const marketEnd = 16 * 60 + 30; // 4:30 PM

  return timeInMinutes >= preMarketStart && timeInMinutes <= marketEnd;
}

/**
 * Transform API response to match our interface.
 * The API returns 'category' but we expose it as 'catalyst_type'.
 */
function transformCatalyst(apiCatalyst: Record<string, unknown>): CatalystItem {
  return {
    symbol: apiCatalyst.symbol as string,
    catalyst_type: apiCatalyst.category as string,
    quality_score: apiCatalyst.quality_score as number,
    headline: apiCatalyst.headline as string,
    summary: apiCatalyst.summary as string,
    source: apiCatalyst.source as string,
    source_url: apiCatalyst.source_url as string | null,
    filing_type: apiCatalyst.filing_type as string | null,
    published_at: apiCatalyst.published_at as string,
    classified_at: apiCatalyst.classified_at as string,
  };
}

/**
 * Fetch wrapper with JWT authentication.
 */
async function fetchWithAuth<T>(endpoint: string): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, { headers });

  if (!response.ok) {
    if (response.status === 401) {
      window.location.href = '/login';
    }
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

// --- API Functions ---

async function getCatalystsBySymbol(symbol: string): Promise<CatalystsResponse> {
  const data = await fetchWithAuth<{
    catalysts: Record<string, unknown>[];
    count: number;
    symbol: string;
  }>(`/catalysts/${symbol}`);

  return {
    catalysts: data.catalysts.map(transformCatalyst),
    count: data.count,
    symbol: data.symbol,
  };
}

async function getRecentCatalysts(limit: number): Promise<CatalystsResponse> {
  const data = await fetchWithAuth<{
    catalysts: Record<string, unknown>[];
    count: number;
    total: number;
  }>(`/catalysts/recent?limit=${limit}`);

  return {
    catalysts: data.catalysts.map(transformCatalyst),
    count: data.count,
    total: data.total,
  };
}

// --- Hooks ---

/**
 * Fetch catalysts for a specific symbol.
 *
 * @param symbol - Stock ticker symbol
 * @returns Query result with catalyst data
 */
export function useCatalystsBySymbol(symbol: string) {
  return useQuery<CatalystsResponse, Error>({
    queryKey: ['catalysts', 'symbol', symbol],
    queryFn: () => getCatalystsBySymbol(symbol),
    enabled: Boolean(symbol),
    staleTime: 60_000, // 1 minute
    refetchInterval: () => (isMarketHours() ? 60_000 : false), // 60s during market hours
    refetchOnWindowFocus: false,
  });
}

/**
 * Fetch recent catalysts across all symbols.
 *
 * @param limit - Maximum number of results (default 50)
 * @returns Query result with recent catalyst data
 */
export function useRecentCatalysts(limit: number = 50) {
  return useQuery<CatalystsResponse, Error>({
    queryKey: ['catalysts', 'recent', limit],
    queryFn: () => getRecentCatalysts(limit),
    staleTime: 30_000, // 30 seconds
    refetchInterval: () => (isMarketHours() ? 30_000 : false), // 30s during market hours
    refetchOnWindowFocus: false,
  });
}
