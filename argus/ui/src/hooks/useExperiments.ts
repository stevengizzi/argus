/**
 * TanStack Query hooks for Experiment Pipeline data.
 *
 * Fetches variant status and promotion events from the experiment REST API.
 * Returns 503 when experiments.enabled=false in the backend config.
 *
 * Sprint 32.5, Session 7.
 */

import { useQuery } from '@tanstack/react-query';
import { getExperimentVariants, getPromotionEvents } from '../api/client';
import type { ExperimentVariantsResponse, PromotionEventsResponse } from '../api/types';

export function useExperimentVariants() {
  return useQuery<ExperimentVariantsResponse, Error>({
    queryKey: ['experiments', 'variants'],
    queryFn: getExperimentVariants,
    staleTime: 30_000,
    refetchInterval: 30_000,
    retry: false, // 503 means disabled — don't retry
  });
}

export interface UsePromotionEventsParams {
  limit?: number;
  offset?: number;
}

export function usePromotionEvents(params?: UsePromotionEventsParams) {
  return useQuery<PromotionEventsResponse, Error>({
    queryKey: ['experiments', 'promotions', params],
    queryFn: () => getPromotionEvents(params),
    staleTime: 30_000,
    refetchInterval: 30_000,
    retry: false,
  });
}
