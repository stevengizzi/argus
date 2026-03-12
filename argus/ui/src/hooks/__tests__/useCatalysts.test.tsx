/**
 * Tests for useCatalysts hooks.
 *
 * Sprint 23.5 Session 5: Frontend — Dashboard Catalyst Badges + Orchestrator Alert Panel
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useCatalystsBySymbol, useRecentCatalysts } from '../useCatalysts';

// Mock the fetch function
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock the getToken function
vi.mock('../../api/client', () => ({
  getToken: vi.fn(() => 'mock-token'),
}));

// Mock usePipelineStatus to return true (pipeline active) for existing tests
vi.mock('../usePipelineStatus', () => ({
  usePipelineStatus: vi.fn(() => true),
}));

const mockCatalystsResponse = {
  catalysts: [
    {
      headline: 'AAPL Q4 Earnings Beat',
      symbol: 'AAPL',
      source: 'SEC',
      source_url: 'https://sec.gov/filing',
      filing_type: '10-K',
      published_at: '2026-03-10T08:00:00Z',
      category: 'earnings',
      quality_score: 85,
      summary: 'Apple beats earnings expectations',
      trading_relevance: 'high',
      classified_by: 'haiku',
      classified_at: '2026-03-10T08:01:00Z',
    },
    {
      headline: 'Insider sells 10,000 shares',
      symbol: 'AAPL',
      source: 'FMP',
      source_url: null,
      filing_type: 'Form 4',
      published_at: '2026-03-10T07:00:00Z',
      category: 'insider_trade',
      quality_score: 65,
      summary: 'Executive sold shares',
      trading_relevance: 'medium',
      classified_by: 'haiku',
      classified_at: '2026-03-10T07:01:00Z',
    },
  ],
  count: 2,
  symbol: 'AAPL',
};

const mockRecentCatalystsResponse = {
  catalysts: mockCatalystsResponse.catalysts,
  count: 2,
  total: 10,
};

describe('useCatalystsBySymbol', () => {
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

  it('returns loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useCatalystsBySymbol('AAPL'), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('returns data on success', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCatalystsResponse),
    });

    const { result } = renderHook(() => useCatalystsBySymbol('AAPL'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.catalysts).toHaveLength(2);
    expect(result.current.data?.catalysts[0].symbol).toBe('AAPL');
    expect(result.current.data?.catalysts[0].catalyst_type).toBe('earnings');
  });

  it('handles error gracefully', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
    });

    const { result } = renderHook(() => useCatalystsBySymbol('AAPL'), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeDefined();
  });

  it('returns empty catalysts array when API returns empty', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ catalysts: [], count: 0, symbol: 'UNKNOWN' }),
    });

    const { result } = renderHook(() => useCatalystsBySymbol('UNKNOWN'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.catalysts).toHaveLength(0);
    expect(result.current.data?.count).toBe(0);
  });

  it('does not fetch when symbol is empty', () => {
    const { result } = renderHook(() => useCatalystsBySymbol(''), { wrapper });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });
});

describe('useRecentCatalysts', () => {
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

  it('returns loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useRecentCatalysts(30), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('returns data on success with default limit', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRecentCatalystsResponse),
    });

    const { result } = renderHook(() => useRecentCatalysts(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.catalysts).toHaveLength(2);
    expect(result.current.data?.total).toBe(10);
  });

  it('uses correct query key with limit', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRecentCatalystsResponse),
    });

    renderHook(() => useRecentCatalysts(25), { wrapper });

    await waitFor(() =>
      expect(queryClient.getQueryState(['catalysts', 'recent', 25])).toBeDefined()
    );
  });
});
