/**
 * TanStack Query hooks for AI endpoints.
 *
 * Sprint 22 Session 6 — Dashboard AI Insight Card + Learning Journal.
 */

import { useQuery } from '@tanstack/react-query';
import {
  getAIStatus,
  getAIInsight,
  getConversations,
  getConversation,
  type ConversationsParams,
} from '../api/client';
import type {
  AIStatusResponse,
  AIInsightResponse,
  ConversationsListResponse,
  ConversationDetailResponse,
} from '../api/types';
import { getMarketContext } from '../utils/marketTime';

/**
 * Default refresh interval for AI insight during market hours (5 minutes).
 */
const DEFAULT_INSIGHT_REFRESH_MS = 5 * 60 * 1000;

/**
 * Hook for fetching AI service status.
 */
export function useAIStatus() {
  return useQuery<AIStatusResponse, Error>({
    queryKey: ['ai', 'status'],
    queryFn: getAIStatus,
    staleTime: 60_000, // 1 minute
  });
}

/**
 * Hook for fetching AI insight for the Dashboard.
 *
 * Auto-refreshes during market hours (9:30 AM - 4:00 PM ET).
 * Disables auto-refresh when market is closed.
 */
export function useAIInsight() {
  const marketContext = getMarketContext();
  const isMarketHours = marketContext.status === 'open';

  return useQuery<AIInsightResponse, Error>({
    queryKey: ['ai', 'insight'],
    queryFn: getAIInsight,
    staleTime: 60_000, // 1 minute
    // Auto-refresh only during market hours
    refetchInterval: isMarketHours ? DEFAULT_INSIGHT_REFRESH_MS : false,
    // Don't refetch on window focus if market is closed
    refetchOnWindowFocus: isMarketHours,
  });
}

/**
 * Filter parameters for conversation list.
 */
export interface ConversationFilters {
  dateFrom?: string;
  dateTo?: string;
  tags?: string[];
  limit?: number;
  offset?: number;
}

/**
 * Hook for fetching conversation list with filters.
 *
 * Supports pagination via limit/offset and filtering by date range and tags.
 */
export function useConversations(filters?: ConversationFilters) {
  // Convert our filter format to API params
  const params: ConversationsParams = {
    date_from: filters?.dateFrom,
    date_to: filters?.dateTo,
    // API only supports single tag filter, so we use the first one if multiple
    tag: filters?.tags?.[0],
    limit: filters?.limit ?? 20,
    offset: filters?.offset ?? 0,
  };

  return useQuery<ConversationsListResponse, Error>({
    queryKey: ['ai', 'conversations', params],
    queryFn: () => getConversations(params),
    staleTime: 30_000, // 30 seconds
  });
}

/**
 * Hook for fetching a single conversation with messages.
 */
export function useConversation(conversationId: string | null) {
  return useQuery<ConversationDetailResponse, Error>({
    queryKey: ['ai', 'conversation', conversationId],
    queryFn: () => getConversation(conversationId!),
    enabled: !!conversationId,
    staleTime: 30_000, // 30 seconds
  });
}
