/**
 * TanStack Query hooks for Learning Loop config proposals.
 *
 * - useConfigProposals() — fetches proposals list with optional status filter
 * - useApproveProposal() — mutation with cache invalidation
 * - useDismissProposal() — mutation with cache invalidation
 * - useRevertProposal() — mutation with cache invalidation
 *
 * Sprint 28, Session 6a.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getConfigProposals,
  approveProposal,
  dismissProposal,
  revertProposal,
} from '../api/learningApi';
import type {
  ProposalsListResponse,
  ProposalActionResponse,
} from '../api/learningApi';

/**
 * Fetch config proposals with optional status filter.
 *
 * @param enabled - Controls whether query fires (for lazy loading). Default true.
 */
export function useConfigProposals(statusFilter?: string, enabled = true) {
  return useQuery<ProposalsListResponse, Error>({
    queryKey: ['learning', 'proposals', { status: statusFilter }],
    queryFn: () =>
      getConfigProposals(statusFilter ? { status: statusFilter } : undefined),
    staleTime: 60_000,
    enabled,
  });
}

/**
 * Approve a PENDING proposal. Invalidates proposals and reports queries.
 */
export function useApproveProposal() {
  const queryClient = useQueryClient();

  return useMutation<
    ProposalActionResponse,
    Error,
    { proposalId: string; notes?: string }
  >({
    mutationFn: ({ proposalId, notes }) => approveProposal(proposalId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learning', 'proposals'] });
      queryClient.invalidateQueries({ queryKey: ['learning', 'reports'] });
      queryClient.invalidateQueries({ queryKey: ['learning', 'report'] });
    },
  });
}

/**
 * Dismiss a PENDING proposal. Invalidates proposals and reports queries.
 */
export function useDismissProposal() {
  const queryClient = useQueryClient();

  return useMutation<
    ProposalActionResponse,
    Error,
    { proposalId: string; notes?: string }
  >({
    mutationFn: ({ proposalId, notes }) => dismissProposal(proposalId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learning', 'proposals'] });
      queryClient.invalidateQueries({ queryKey: ['learning', 'reports'] });
      queryClient.invalidateQueries({ queryKey: ['learning', 'report'] });
    },
  });
}

/**
 * Revert an APPLIED proposal. Invalidates proposals and reports queries.
 */
export function useRevertProposal() {
  const queryClient = useQueryClient();

  return useMutation<
    ProposalActionResponse,
    Error,
    { proposalId: string; notes?: string }
  >({
    mutationFn: ({ proposalId, notes }) => revertProposal(proposalId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learning', 'proposals'] });
      queryClient.invalidateQueries({ queryKey: ['learning', 'reports'] });
      queryClient.invalidateQueries({ queryKey: ['learning', 'report'] });
    },
  });
}
