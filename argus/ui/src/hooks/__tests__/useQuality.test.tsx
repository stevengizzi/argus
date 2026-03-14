/**
 * Tests for useQuality hooks.
 *
 * Sprint 24 Session 9.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock getToken
vi.mock('../../api/client', async () => {
  const actual = await vi.importActual('../../api/client');
  return {
    ...actual,
    getToken: vi.fn(() => 'mock-token'),
  };
});

const { useQualityScore, useQualityDistribution } = await import('../useQuality');

describe('useQualityScore', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('fetches quality score for symbol', async () => {
    const mockData = {
      symbol: 'AAPL',
      score: 85.5,
      grade: 'A',
      risk_tier: '2.0%',
      components: { ps: 80, cq: 70, vp: 90, hm: 85, ra: 75 },
      scored_at: '2026-03-14T10:00:00Z',
    };

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const { result } = renderHook(() => useQualityScore('AAPL'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.grade).toBe('A');
    expect(result.current.data?.score).toBe(85.5);
    expect(result.current.data?.components.ps).toBe(80);
  });

  it('does not fetch when symbol is empty', async () => {
    const { result } = renderHook(() => useQualityScore(''), { wrapper });

    await new Promise((r) => setTimeout(r, 50));
    expect(mockFetch).not.toHaveBeenCalled();
    expect(result.current.isFetching).toBe(false);
  });
});

describe('useQualityDistribution', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('fetches grade distribution', async () => {
    const mockData = {
      grades: { 'A+': 2, 'A': 5, 'A-': 3, 'B+': 4, 'B': 2, 'B-': 1, 'C+': 0, 'C': 0 },
      total: 17,
      filtered: 1,
    };

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const { result } = renderHook(() => useQualityDistribution(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total).toBe(17);
    expect(result.current.data?.grades['A+']).toBe(2);
  });
});
