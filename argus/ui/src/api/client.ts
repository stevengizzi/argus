/**
 * Argus Command Center API client.
 *
 * Provides typed fetch wrappers for all API endpoints with JWT authentication.
 */

import type {
  AccountResponse,
  BarsResponse,
  Briefing,
  BriefingsListResponse,
  CorrelationResponse,
  DebriefSearchResponse,
  DecisionsResponse,
  DistributionResponse,
  DocumentsListResponse,
  DocumentTagsResponse,
  GoalsConfig,
  HeatmapResponse,
  HealthResponse,
  JournalEntriesListResponse,
  JournalEntry,
  JournalTagsResponse,
  LoginRequest,
  OrchestratorStatusResponse,
  PerformancePeriod,
  PerformanceResponse,
  PositionsResponse,
  ResearchDocument,
  SessionSummaryResponse,
  StrategiesResponse,
  StrategySpecResponse,
  ThrottleOverrideRequest,
  TokenResponse,
  TradeReplayResponse,
  TradesBatchResponse,
  TradesResponse,
  WatchlistResponse,
} from './types';

const API_BASE = '/api/v1';

/**
 * Custom error class that preserves HTTP status codes.
 *
 * Use this instead of generic Error to enable status-code-specific
 * error handling (e.g., 409 Conflict for duplicate briefings).
 */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

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
    const errorBody = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(errorBody.detail || `HTTP ${response.status}`, response.status);
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

export async function getTradesByIds(ids: string[]): Promise<TradesBatchResponse> {
  if (ids.length === 0) {
    return { trades: [], count: 0, timestamp: new Date().toISOString() };
  }
  return fetchWithAuth<TradesBatchResponse>(`/trades/batch?ids=${ids.join(',')}`);
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

export async function getOrchestratorDecisions(
  date?: string
): Promise<DecisionsResponse> {
  const params = new URLSearchParams();
  params.set('limit', '100');
  if (date) params.set('date', date);
  return fetchWithAuth<DecisionsResponse>(`/orchestrator/decisions?${params}`);
}

export async function triggerRebalance(): Promise<{ success: boolean; message: string }> {
  return fetchWithAuth('/orchestrator/rebalance', { method: 'POST' });
}

export async function overrideThrottle(
  strategyId: string,
  body: ThrottleOverrideRequest
): Promise<{ success: boolean; message: string }> {
  return fetchWithAuth(`/orchestrator/strategies/${strategyId}/override-throttle`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
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

// Debrief — Briefings endpoints
export interface BriefingsParams {
  briefing_type?: 'pre_market' | 'eod';
  status?: 'draft' | 'final' | 'ai_generated';
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export async function fetchBriefings(
  params?: BriefingsParams
): Promise<BriefingsListResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return fetchWithAuth<BriefingsListResponse>(`/debrief/briefings${query ? `?${query}` : ''}`);
}

export async function fetchBriefing(id: string): Promise<Briefing> {
  return fetchWithAuth<Briefing>(`/debrief/briefings/${id}`);
}

export interface CreateBriefingData {
  date: string;
  briefing_type: 'pre_market' | 'eod';
  title?: string;
}

export async function createBriefing(data: CreateBriefingData): Promise<Briefing> {
  return fetchWithAuth<Briefing>('/debrief/briefings', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export interface UpdateBriefingData {
  title?: string;
  content?: string;
  status?: 'draft' | 'final' | 'ai_generated';
  metadata?: Record<string, unknown>;
}

export async function updateBriefing(
  id: string,
  data: UpdateBriefingData
): Promise<Briefing> {
  return fetchWithAuth<Briefing>(`/debrief/briefings/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteBriefing(id: string): Promise<void> {
  await fetchWithAuth<void>(`/debrief/briefings/${id}`, {
    method: 'DELETE',
  });
}

// Debrief — Documents endpoints
export async function fetchDocuments(
  category?: string
): Promise<DocumentsListResponse> {
  const searchParams = new URLSearchParams();
  if (category) {
    searchParams.set('category', category);
  }
  const query = searchParams.toString();
  return fetchWithAuth<DocumentsListResponse>(`/debrief/documents${query ? `?${query}` : ''}`);
}

export async function fetchDocument(id: string): Promise<ResearchDocument> {
  return fetchWithAuth<ResearchDocument>(`/debrief/documents/${id}`);
}

export interface CreateDocumentData {
  category: string;
  title: string;
  content: string;
  tags?: string[];
}

export async function createDocument(data: CreateDocumentData): Promise<ResearchDocument> {
  return fetchWithAuth<ResearchDocument>('/debrief/documents', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export interface UpdateDocumentData {
  title?: string;
  content?: string;
  category?: string;
  tags?: string[];
}

export async function updateDocument(
  id: string,
  data: UpdateDocumentData
): Promise<ResearchDocument> {
  return fetchWithAuth<ResearchDocument>(`/debrief/documents/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteDocument(id: string): Promise<void> {
  await fetchWithAuth<void>(`/debrief/documents/${id}`, {
    method: 'DELETE',
  });
}

export async function fetchDocumentTags(): Promise<DocumentTagsResponse> {
  return fetchWithAuth<DocumentTagsResponse>('/debrief/documents/tags');
}

// Debrief — Journal endpoints
export interface JournalParams {
  entry_type?: string;
  strategy_id?: string;
  tag?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export async function fetchJournalEntries(
  params?: JournalParams
): Promise<JournalEntriesListResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return fetchWithAuth<JournalEntriesListResponse>(`/debrief/journal${query ? `?${query}` : ''}`);
}

export async function fetchJournalEntry(id: string): Promise<JournalEntry> {
  return fetchWithAuth<JournalEntry>(`/debrief/journal/${id}`);
}

export interface CreateJournalEntryData {
  entry_type: 'observation' | 'trade_annotation' | 'pattern_note' | 'system_note';
  title: string;
  content: string;
  linked_strategy_id?: string;
  linked_trade_ids?: string[];
  tags?: string[];
}

export async function createJournalEntry(data: CreateJournalEntryData): Promise<JournalEntry> {
  return fetchWithAuth<JournalEntry>('/debrief/journal', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export interface UpdateJournalEntryData {
  title?: string;
  content?: string;
  entry_type?: 'observation' | 'trade_annotation' | 'pattern_note' | 'system_note';
  linked_strategy_id?: string;
  linked_trade_ids?: string[];
  tags?: string[];
}

export async function updateJournalEntry(
  id: string,
  data: UpdateJournalEntryData
): Promise<JournalEntry> {
  return fetchWithAuth<JournalEntry>(`/debrief/journal/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteJournalEntry(id: string): Promise<void> {
  await fetchWithAuth<void>(`/debrief/journal/${id}`, {
    method: 'DELETE',
  });
}

export async function fetchJournalTags(): Promise<JournalTagsResponse> {
  return fetchWithAuth<JournalTagsResponse>('/debrief/journal/tags');
}

// Debrief — Search endpoint
export async function fetchDebriefSearch(
  query: string,
  scope?: 'all' | 'briefings' | 'journal' | 'documents'
): Promise<DebriefSearchResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('query', query);
  if (scope) {
    searchParams.set('scope', scope);
  }
  return fetchWithAuth<DebriefSearchResponse>(`/debrief/search?${searchParams}`);
}

// Performance analytics endpoints (Sprint 21d)
export async function getHeatmapData(
  period: PerformancePeriod,
  strategyId?: string
): Promise<HeatmapResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('period', period);
  if (strategyId) {
    searchParams.set('strategy_id', strategyId);
  }
  return fetchWithAuth<HeatmapResponse>(`/performance/heatmap?${searchParams}`);
}

export async function getDistribution(
  period: PerformancePeriod,
  strategyId?: string
): Promise<DistributionResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('period', period);
  if (strategyId) {
    searchParams.set('strategy_id', strategyId);
  }
  return fetchWithAuth<DistributionResponse>(`/performance/distribution?${searchParams}`);
}

export async function getCorrelation(
  period: PerformancePeriod
): Promise<CorrelationResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('period', period);
  return fetchWithAuth<CorrelationResponse>(`/performance/correlation?${searchParams}`);
}

// Trade replay endpoint
export async function getTradeReplay(tradeId: string): Promise<TradeReplayResponse> {
  return fetchWithAuth<TradeReplayResponse>(`/trades/${tradeId}/replay`);
}

// Config endpoints
export async function getGoalsConfig(): Promise<GoalsConfig> {
  return fetchWithAuth<GoalsConfig>('/config/goals');
}
