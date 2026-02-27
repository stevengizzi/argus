/**
 * TanStack Query hooks for research documents data.
 *
 * Provides queries and mutations for CRUD operations on documents.
 * Documents can be from filesystem (read-only) or database (full CRUD).
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import {
  fetchDocuments,
  fetchDocument,
  createDocument,
  updateDocument,
  deleteDocument,
  fetchDocumentTags,
  type CreateDocumentData,
  type UpdateDocumentData,
} from '../api/client';
import type { DocumentsListResponse, ResearchDocument, DocumentTagsResponse } from '../api/types';

/**
 * Fetch list of documents with optional category filter.
 */
export function useDocuments(category?: string) {
  return useQuery<DocumentsListResponse, Error>({
    queryKey: ['documents', category],
    queryFn: () => fetchDocuments(category),
    refetchInterval: 60_000, // 60 seconds
    placeholderData: keepPreviousData, // Keep showing previous results while filtering
  });
}

/**
 * Fetch a single document by ID.
 */
export function useDocument(id: string | null) {
  return useQuery<ResearchDocument, Error>({
    queryKey: ['document', id],
    queryFn: () => fetchDocument(id!),
    enabled: !!id,
  });
}

/**
 * Create a new database document.
 */
export function useCreateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateDocumentData) => createDocument(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

/**
 * Update an existing database document.
 */
export function useUpdateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateDocumentData }) =>
      updateDocument(id, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document', variables.id] });
    },
  });
}

/**
 * Delete a database document.
 */
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

/**
 * Fetch all unique document tags.
 */
export function useDocumentTags() {
  return useQuery<DocumentTagsResponse, Error>({
    queryKey: ['document-tags'],
    queryFn: fetchDocumentTags,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
