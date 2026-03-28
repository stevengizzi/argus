/**
 * Learning Loop API client.
 *
 * Typed fetch wrappers for all 8 learning endpoints.
 * Interfaces match backend Pydantic models in argus/api/routes/learning.py.
 *
 * Sprint 28, Session 6a.
 */

import { getToken, clearToken, ApiError } from './client';

const API_BASE = '/api/v1';

// --- TypeScript Interfaces ---

export type ConfidenceLevel = 'HIGH' | 'MODERATE' | 'LOW' | 'INSUFFICIENT_DATA';

export type ProposalStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'DISMISSED'
  | 'SUPERSEDED'
  | 'REJECTED_GUARD'
  | 'REJECTED_VALIDATION'
  | 'APPLIED'
  | 'REVERTED';

export interface WeightRecommendation {
  dimension: string;
  current_weight: number;
  recommended_weight: number;
  delta: number;
  correlation_trade_source: number | null;
  correlation_counterfactual_source: number | null;
  p_value: number | null;
  sample_size: number;
  confidence: ConfidenceLevel;
  regime_breakdown: Record<string, number>;
  source_divergence_flag: boolean;
}

export interface ThresholdRecommendation {
  grade: string;
  current_threshold: number;
  recommended_direction: 'raise' | 'lower';
  missed_opportunity_rate: number;
  correct_rejection_rate: number;
  sample_size: number;
  confidence: ConfidenceLevel;
}

export interface CorrelationResult {
  strategy_pairs: [string, string][];
  correlation_matrix: Record<string, number>;
  flagged_pairs: [string, string][];
  excluded_strategies: string[];
  window_days: number;
}

export interface DataQualityPreamble {
  trading_days_count: number;
  total_trades: number;
  total_counterfactual: number;
  effective_sample_size: number;
  known_data_gaps: string[];
  earliest_date: string | null;
  latest_date: string | null;
}

export interface LearningReport {
  report_id: string;
  generated_at: string;
  analysis_window_start: string;
  analysis_window_end: string;
  data_quality: DataQualityPreamble;
  weight_recommendations: WeightRecommendation[];
  threshold_recommendations: ThresholdRecommendation[];
  correlation_result: CorrelationResult | null;
  version: number;
}

export interface ConfigProposal {
  proposal_id: string;
  report_id: string;
  field_path: string;
  current_value: number;
  proposed_value: number;
  rationale: string;
  status: ProposalStatus;
  created_at: string;
  updated_at: string;
  human_notes: string | null;
}

export interface ConfigChangeEntry {
  change_id: number;
  proposal_id: string | null;
  field_path: string;
  old_value: number;
  new_value: number;
  source: string;
  applied_at: string;
  report_id: string | null;
}

// --- Response types ---

export interface TriggerResponse {
  report_id: string;
  generated_at: string;
  weight_recommendations: number;
  threshold_recommendations: number;
  proposals_generated: number;
  timestamp: string;
}

export interface ReportSummary {
  report_id: string;
  generated_at: string;
  analysis_window_start: string;
  analysis_window_end: string;
  weight_recommendations: number;
  threshold_recommendations: number;
  version: number;
}

export interface ReportsListResponse {
  reports: ReportSummary[];
  count: number;
  timestamp: string;
}

export interface ReportDetailResponse {
  report: LearningReport;
  timestamp: string;
}

export interface ProposalsListResponse {
  proposals: ConfigProposal[];
  count: number;
  timestamp: string;
}

export interface ProposalActionResponse {
  proposal: ConfigProposal;
  timestamp: string;
}

export interface ChangeHistoryResponse {
  changes: ConfigChangeEntry[];
  count: number;
  timestamp: string;
}

// --- Fetch helper (mirrors client.ts pattern) ---

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

// --- API functions ---

/** POST /learning/trigger — run analysis pipeline. */
export async function triggerLearningAnalysis(): Promise<TriggerResponse> {
  return fetchWithAuth<TriggerResponse>('/learning/trigger', { method: 'POST' });
}

/** GET /learning/reports — list reports with optional date filters. */
export async function getLearningReports(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<ReportsListResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return fetchWithAuth<ReportsListResponse>(`/learning/reports${query ? `?${query}` : ''}`);
}

/** GET /learning/reports/:id — get a single report with full details. */
export async function getLearningReport(reportId: string): Promise<ReportDetailResponse> {
  return fetchWithAuth<ReportDetailResponse>(`/learning/reports/${reportId}`);
}

/** GET /learning/proposals — list config proposals. */
export async function getConfigProposals(params?: {
  status?: string;
  report_id?: string;
}): Promise<ProposalsListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) {
    searchParams.set('status', params.status);
  }
  if (params?.report_id) {
    searchParams.set('report_id', params.report_id);
  }
  const query = searchParams.toString();
  return fetchWithAuth<ProposalsListResponse>(`/learning/proposals${query ? `?${query}` : ''}`);
}

/** POST /learning/proposals/:id/approve */
export async function approveProposal(
  proposalId: string,
  notes?: string
): Promise<ProposalActionResponse> {
  const body = notes !== undefined ? { notes } : undefined;
  return fetchWithAuth<ProposalActionResponse>(
    `/learning/proposals/${proposalId}/approve`,
    {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }
  );
}

/** POST /learning/proposals/:id/dismiss */
export async function dismissProposal(
  proposalId: string,
  notes?: string
): Promise<ProposalActionResponse> {
  const body = notes !== undefined ? { notes } : undefined;
  return fetchWithAuth<ProposalActionResponse>(
    `/learning/proposals/${proposalId}/dismiss`,
    {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }
  );
}

/** POST /learning/proposals/:id/revert */
export async function revertProposal(
  proposalId: string,
  notes?: string
): Promise<ProposalActionResponse> {
  const body = notes !== undefined ? { notes } : undefined;
  return fetchWithAuth<ProposalActionResponse>(
    `/learning/proposals/${proposalId}/revert`,
    {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }
  );
}

/** GET /learning/config-history — config change audit trail. */
export async function getConfigHistory(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<ChangeHistoryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.start_date) {
    searchParams.set('start_date', params.start_date);
  }
  if (params?.end_date) {
    searchParams.set('end_date', params.end_date);
  }
  const query = searchParams.toString();
  return fetchWithAuth<ChangeHistoryResponse>(
    `/learning/config-history${query ? `?${query}` : ''}`
  );
}
