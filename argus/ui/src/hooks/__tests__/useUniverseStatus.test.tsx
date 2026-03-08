/**
 * Tests for useUniverseStatus hook.
 *
 * Sprint 23: NLP Catalyst + Universe Manager
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useUniverseStatus } from '../useUniverseStatus';
import type { UniverseStatusResponse } from '../../api/types';

// Mock the API client
vi.mock('../../api/client', () => ({
  getUniverseStatus: vi.fn(),
}));

import { getUniverseStatus } from '../../api/client';

const mockGetUniverseStatus = vi.mocked(getUniverseStatus);

const mockEnabledResponse: UniverseStatusResponse = {
  enabled: true,
  total_symbols: 5000,
  viable_count: 2847,
  per_strategy_counts: {
    orb_breakout: 1245,
    vwap_reclaim: 1534,
  },
  last_refresh: '2026-03-08T14:30:00Z',
  reference_data_age_minutes: 45,
};

describe('useUniverseStatus', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('returns correct data shape when successful', async () => {
    mockGetUniverseStatus.mockResolvedValue(mockEnabledResponse);

    const { result } = renderHook(() => useUniverseStatus(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockEnabledResponse);
    expect(result.current.data?.enabled).toBe(true);
    expect(result.current.data?.viable_count).toBe(2847);
    expect(result.current.data?.per_strategy_counts).toHaveProperty('orb_breakout');
  });

  it('returns isLoading true while fetching', () => {
    // Never resolve the promise to keep loading state
    mockGetUniverseStatus.mockImplementation(
      () => new Promise(() => {})
    );

    const { result } = renderHook(() => useUniverseStatus(), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('returns error when fetch fails', async () => {
    const error = new Error('Network error');
    mockGetUniverseStatus.mockRejectedValue(error);

    const { result } = renderHook(() => useUniverseStatus(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toEqual(error);
  });

  it('uses correct query key', async () => {
    mockGetUniverseStatus.mockResolvedValue(mockEnabledResponse);

    renderHook(() => useUniverseStatus(), { wrapper });

    await waitFor(() =>
      expect(queryClient.getQueryState(['universe-status'])).toBeDefined()
    );
  });
});
