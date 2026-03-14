/**
 * TanStack Query hooks for quality scoring data.
 *
 * Provides hooks for fetching quality scores, history, and grade distribution
 * from the Quality Engine API endpoints.
 *
 * Sprint 24 Session 9.
 */

import { useQuery } from '@tanstack/react-query';
import {
  getQualityScore,
  getQualityHistory,
  getQualityDistribution,
} from '../api/client';
import type { QualityHistoryParams } from '../api/client';
import type {
  QualityScoreResponse,
  QualityHistoryResponse,
  GradeDistributionResponse,
} from '../api/types';

export function useQualityScore(symbol: string) {
  return useQuery<QualityScoreResponse, Error>({
    queryKey: ['quality', 'score', symbol],
    queryFn: () => getQualityScore(symbol),
    staleTime: 30_000,
    refetchInterval: 30_000,
    refetchOnWindowFocus: false,
    enabled: Boolean(symbol),
  });
}

export interface QualityHistoryFilters {
  symbol?: string;
  strategy_id?: string;
  grade?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

export function useQualityHistory(filters?: QualityHistoryFilters) {
  const params: QualityHistoryParams | undefined = filters
    ? {
        symbol: filters.symbol,
        strategy_id: filters.strategy_id,
        grade: filters.grade,
        start_date: filters.start_date,
        end_date: filters.end_date,
        limit: filters.limit,
        offset: filters.offset,
      }
    : undefined;

  return useQuery<QualityHistoryResponse, Error>({
    queryKey: ['quality', 'history', params],
    queryFn: () => getQualityHistory(params),
    staleTime: 30_000,
    refetchInterval: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useQualityDistribution() {
  return useQuery<GradeDistributionResponse, Error>({
    queryKey: ['quality', 'distribution'],
    queryFn: () => getQualityDistribution(),
    staleTime: 30_000,
    refetchInterval: 30_000,
    refetchOnWindowFocus: false,
  });
}
