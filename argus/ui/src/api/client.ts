/**
 * Argus Command Center API client.
 *
 * Provides typed fetch wrappers for all API endpoints with JWT authentication.
 */

import type {
  AccountResponse,
  BarsResponse,
  HealthResponse,
  LoginRequest,
  OrchestratorStatusResponse,
  PerformancePeriod,
  PerformanceResponse,
  PositionsResponse,
  SessionSummaryResponse,
  StrategiesResponse,
  StrategySpecResponse,
  TokenResponse,
  TradesResponse,
  WatchlistResponse,
} from './types';

const API_BASE = '/api/v1';

/**
 * Get the stored JWT token from localStorage.
 */
export function getToken(): string | null {
  return localStorage.getItem('argus_token');
}

/**
 * Set the JWT token in localStorage.
 */
export function setToken(token: string): void {
  localStorage.setItem('argus_token', token);
}

/**
 * Remove the JWT token from localStorage.
 */
export function clearToken(): void {
  localStorage.removeItem('argus_token');
}

/**
 * Fetch wrapper with JWT authentication header.
 */
async function fetchWithAuth<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  headers.set('Content-Type', 'application/json');

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      clearToken();
      window.location.href = '/login';
    }
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Auth endpoints
export async function login(password: string): Promise<TokenResponse> {
  const request: LoginRequest = { password };
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(error.detail || 'Login failed');
  }

  const data: TokenResponse = await response.json();
  setToken(data.access_token);
  return data;
}

export function logout(): void {
  clearToken();
  window.location.href = '/login';
}

export async function refreshToken(): Promise<TokenResponse> {
  return fetchWithAuth<TokenResponse>('/auth/refresh', { method: 'POST' });
}

// Account endpoints
export async function getAccount(): Promise<AccountResponse> {
  return fetchWithAuth<AccountResponse>('/account');
}

// Position endpoints
export async function getPositions(params?: {
  strategy_id?: string;
}): Promise<PositionsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.strategy_id) {
    searchParams.set('strategy_id', params.strategy_id);
  }
  const query = searchParams.toString();
  return fetchWithAuth<PositionsResponse>(`/positions${query ? `?${query}` : ''}`);
}

// Trade endpoints
export async function getTrades(params?: {
  strategy_id?: string;
  symbol?: string;
  date_from?: string;
  date_to?: string;
  outcome?: 'win' | 'loss' | 'breakeven';
  limit?: number;
  offset?: number;
}): Promise<TradesResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return fetchWithAuth<TradesResponse>(`/trades${query ? `?${query}` : ''}`);
}

// Performance endpoints
export async function getPerformance(
  period: PerformancePeriod,
  strategyId?: string
): Promise<PerformanceResponse> {
  const searchParams = new URLSearchParams();
  if (strategyId) {
    searchParams.set('strategy_id', strategyId);
  }
  const query = searchParams.toString();
  return fetchWithAuth<PerformanceResponse>(`/performance/${period}${query ? `?${query}` : ''}`);
}

// Health endpoints
export async function getHealth(): Promise<HealthResponse> {
  return fetchWithAuth<HealthResponse>('/health');
}

// Strategy endpoints
export async function getStrategies(): Promise<StrategiesResponse> {
  return fetchWithAuth<StrategiesResponse>('/strategies');
}

// Orchestrator endpoints
export async function getOrchestratorStatus(): Promise<OrchestratorStatusResponse> {
  return fetchWithAuth<OrchestratorStatusResponse>('/orchestrator/status');
}

// Session summary endpoints
export async function getSessionSummary(
  date?: string
): Promise<SessionSummaryResponse> {
  const query = date ? `?date=${date}` : '';
  return fetchWithAuth<SessionSummaryResponse>(`/session-summary${query}`);
}

// Watchlist endpoints
export async function getWatchlist(): Promise<WatchlistResponse> {
  return fetchWithAuth<WatchlistResponse>('/watchlist');
}

// Strategy spec endpoints (Pattern Library)
export async function fetchStrategySpec(strategyId: string): Promise<StrategySpecResponse> {
  return fetchWithAuth<StrategySpecResponse>(`/strategies/${strategyId}/spec`);
}

// Market data endpoints
export async function fetchSymbolBars(
  symbol: string,
  limit: number = 390
): Promise<BarsResponse> {
  const searchParams = new URLSearchParams();
  if (limit !== 390) {
    searchParams.set('limit', String(limit));
  }
  const query = searchParams.toString();
  return fetchWithAuth<BarsResponse>(`/market/${symbol}/bars${query ? `?${query}` : ''}`);
}
