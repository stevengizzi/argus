/**
 * TanStack Query hooks for briefings data.
 *
 * Provides queries and mutations for CRUD operations on briefings.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchBriefings,
  fetchBriefing,
  createBriefing,
  updateBriefing,
  deleteBriefing,
  type BriefingsParams,
  type CreateBriefingData,
  type UpdateBriefingData,
} from '../api/client';
import type { BriefingsListResponse, Briefing } from '../api/types';

/**
 * Fetch list of briefings with optional filters.
 */
export function useBriefings(filters?: BriefingsParams) {
  return useQuery<BriefingsListResponse, Error>({
    queryKey: ['briefings', filters],
    queryFn: () => fetchBriefings(filters),
    refetchInterval: 30_000, // 30 seconds
  });
}

/**
 * Fetch a single briefing by ID.
 */
export function useBriefing(id: string | null) {
  return useQuery<Briefing, Error>({
    queryKey: ['briefing', id],
    queryFn: () => fetchBriefing(id!),
    enabled: !!id,
  });
}

/**
 * Create a new briefing.
 */
export function useCreateBriefing() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateBriefingData) => createBriefing(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['briefings'] });
    },
  });
}

/**
 * Update an existing briefing.
 */
export function useUpdateBriefing() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateBriefingData }) =>
      updateBriefing(id, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['briefings'] });
      queryClient.invalidateQueries({ queryKey: ['briefing', variables.id] });
    },
  });
}

/**
 * Delete a briefing.
 */
export function useDeleteBriefing() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteBriefing(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['briefings'] });
    },
  });
}
