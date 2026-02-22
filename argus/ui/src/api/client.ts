/**
 * Argus Command Center API client.
 *
 * Provides typed fetch wrappers for all API endpoints with JWT authentication.
 */

import type {
  AccountInfo,
  DailyPnlResponse,
  HealthResponse,
  LoginRequest,
  LoginResponse,
  PerformanceMetrics,
  PositionsResponse,
  StrategiesResponse,
  TradesResponse,
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
export async function login(password: string): Promise<LoginResponse> {
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

  const data: LoginResponse = await response.json();
  setToken(data.access_token);
  return data;
}

export function logout(): void {
  clearToken();
  window.location.href = '/login';
}

export async function refreshToken(): Promise<LoginResponse> {
  return fetchWithAuth<LoginResponse>('/auth/refresh', { method: 'POST' });
}

// Account endpoints
export async function getAccount(): Promise<AccountInfo> {
  return fetchWithAuth<AccountInfo>('/account');
}

// Position endpoints
export async function getPositions(): Promise<PositionsResponse> {
  return fetchWithAuth<PositionsResponse>('/positions');
}

// Trade endpoints
export async function getTrades(params?: {
  strategy_id?: string;
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
export async function getPerformance(params?: {
  strategy_id?: string;
  date_from?: string;
  date_to?: string;
}): Promise<PerformanceMetrics> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return fetchWithAuth<PerformanceMetrics>(`/performance${query ? `?${query}` : ''}`);
}

export async function getDailyPnl(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<DailyPnlResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return fetchWithAuth<DailyPnlResponse>(`/performance/daily${query ? `?${query}` : ''}`);
}

// Health endpoints
export async function getHealth(): Promise<HealthResponse> {
  return fetchWithAuth<HealthResponse>('/health');
}

// Strategy endpoints
export async function getStrategies(): Promise<StrategiesResponse> {
  return fetchWithAuth<StrategiesResponse>('/strategies');
}
