/**
 * TanStack Query hooks for journal entries data.
 *
 * Provides queries and mutations for CRUD operations on journal entries.
 * Includes optimistic update pattern for create mutation.
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import {
  fetchJournalEntries,
  fetchJournalEntry,
  createJournalEntry,
  updateJournalEntry,
  deleteJournalEntry,
  fetchJournalTags,
  type JournalParams,
  type CreateJournalEntryData,
  type UpdateJournalEntryData,
} from '../api/client';
import type { JournalEntriesListResponse, JournalEntry, JournalTagsResponse } from '../api/types';

/**
 * Fetch list of journal entries with optional filters.
 */
export function useJournalEntries(filters?: JournalParams) {
  return useQuery<JournalEntriesListResponse, Error>({
    queryKey: ['journal', filters],
    queryFn: () => fetchJournalEntries(filters),
    refetchInterval: 30_000, // 30 seconds
    placeholderData: keepPreviousData, // Keep showing previous results while filtering
  });
}

/**
 * Fetch a single journal entry by ID.
 */
export function useJournalEntry(id: string | null) {
  return useQuery<JournalEntry, Error>({
    queryKey: ['journal-entry', id],
    queryFn: () => fetchJournalEntry(id!),
    enabled: !!id,
  });
}

/**
 * Create a new journal entry with optimistic update.
 */
export function useCreateJournalEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateJournalEntryData) => createJournalEntry(data),
    onMutate: async (newEntry) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['journal'] });

      // Snapshot the previous value
      const previousEntries = queryClient.getQueryData<JournalEntriesListResponse>(['journal']);

      // Optimistically add the new entry (with a temporary ID)
      if (previousEntries) {
        const optimisticEntry: JournalEntry = {
          id: `temp-${Date.now()}`,
          entry_type: newEntry.entry_type,
          title: newEntry.title,
          content: newEntry.content,
          author: 'user',
          linked_strategy_id: newEntry.linked_strategy_id ?? null,
          linked_trade_ids: newEntry.linked_trade_ids ?? [],
          tags: newEntry.tags ?? [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };

        queryClient.setQueryData<JournalEntriesListResponse>(['journal'], {
          entries: [optimisticEntry, ...previousEntries.entries],
          total: previousEntries.total + 1,
        });
      }

      return { previousEntries };
    },
    onError: (_err, _newEntry, context) => {
      // Rollback to the previous value on error
      if (context?.previousEntries) {
        queryClient.setQueryData(['journal'], context.previousEntries);
      }
    },
    onSettled: () => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: ['journal'] });
      // Invalidate tags in case new tags were added
      queryClient.invalidateQueries({ queryKey: ['journal-tags'] });
    },
  });
}

/**
 * Update an existing journal entry.
 */
export function useUpdateJournalEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateJournalEntryData }) =>
      updateJournalEntry(id, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['journal'] });
      queryClient.invalidateQueries({ queryKey: ['journal-entry', variables.id] });
      // Invalidate tags in case tags were modified
      queryClient.invalidateQueries({ queryKey: ['journal-tags'] });
    },
  });
}

/**
 * Delete a journal entry.
 */
export function useDeleteJournalEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteJournalEntry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal'] });
    },
  });
}

/**
 * Fetch all unique journal tags.
 */
export function useJournalTags() {
  return useQuery<JournalTagsResponse, Error>({
    queryKey: ['journal-tags'],
    queryFn: fetchJournalTags,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
