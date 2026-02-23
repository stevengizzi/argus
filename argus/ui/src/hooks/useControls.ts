/**
 * TanStack Query hooks for control operations.
 *
 * Provides mutations for:
 * - Pausing/resuming strategies
 * - Closing individual positions
 * - Emergency flatten all
 * - Emergency pause all
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { getToken } from '../api/client';

interface ControlResponse {
  success: boolean;
  message: string;
  timestamp: string;
}

/**
 * Generic POST request helper for control endpoints.
 */
async function controlPost(endpoint: string): Promise<ControlResponse> {
  const token = getToken();
  const response = await fetch(`/api/v1/controls${endpoint}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Hook to pause a strategy.
 */
export function usePauseStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategyId: string) => controlPost(`/strategies/${strategyId}/pause`),
    onSuccess: () => {
      // Invalidate strategies to refresh the list
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}

/**
 * Hook to resume a strategy.
 */
export function useResumeStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategyId: string) => controlPost(`/strategies/${strategyId}/resume`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}

/**
 * Hook to close a specific position.
 */
export function useClosePosition() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (positionId: string) => controlPost(`/positions/${positionId}/close`),
    onSuccess: () => {
      // Invalidate positions and account data
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['account'] });
    },
  });
}

/**
 * Hook to emergency flatten all positions.
 */
export function useEmergencyFlatten() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => controlPost('/emergency/flatten'),
    onSuccess: () => {
      // Invalidate positions, account, and trades
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['account'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
    },
  });
}

/**
 * Hook to emergency pause all strategies.
 */
export function useEmergencyPauseAll() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => controlPost('/emergency/pause'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}
