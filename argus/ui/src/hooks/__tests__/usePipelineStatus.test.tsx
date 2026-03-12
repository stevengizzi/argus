/**
 * Tests for usePipelineStatus and catalyst/intelligence hook gating.
 *
 * Sprint 23.9 Session 1 — DEF-041: Gate catalyst/intelligence hooks on
 * pipeline status from health endpoint.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock the health hook
const mockUseHealth = vi.fn();
vi.mock('../useHealth', () => ({
  useHealth: () => mockUseHealth(),
}));

// Mock fetch for catalyst/briefing hooks
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock getToken
vi.mock('../../api/client', () => ({
  getToken: vi.fn(() => 'mock-token'),
}));

// Import after mocks are set up
const { usePipelineStatus } = await import('../usePipelineStatus');
const { useCatalystsBySymbol, useRecentCatalysts } = await import('../useCatalysts');
const { useIntelligenceBriefing, useIntelligenceBriefingHistory } = await import(
  '../useIntelligenceBriefings'
);

describe('usePipelineStatus', () => {
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

  it('returns false when health endpoint is loading', () => {
    mockUseHealth.mockReturnValue({ data: undefined, isSuccess: false });
    const { result } = renderHook(() => usePipelineStatus(), { wrapper });
    expect(result.current).toBe(false);
  });

  it('returns false when health endpoint fails', () => {
    mockUseHealth.mockReturnValue({ data: undefined, isSuccess: false, isError: true });
    const { result } = renderHook(() => usePipelineStatus(), { wrapper });
    expect(result.current).toBe(false);
  });

  it('returns false when pipeline component is absent', () => {
    mockUseHealth.mockReturnValue({
      data: {
        status: 'healthy',
        components: {
          broker: { status: 'healthy', details: 'Connected' },
        },
      },
      isSuccess: true,
    });
    const { result } = renderHook(() => usePipelineStatus(), { wrapper });
    expect(result.current).toBe(false);
  });

  it('returns true when pipeline component is healthy', () => {
    mockUseHealth.mockReturnValue({
      data: {
        status: 'healthy',
        components: {
          broker: { status: 'healthy', details: 'Connected' },
          catalyst_pipeline: { status: 'healthy', details: '3 sources active' },
        },
      },
      isSuccess: true,
    });
    const { result } = renderHook(() => usePipelineStatus(), { wrapper });
    expect(result.current).toBe(true);
  });

  it('returns false when pipeline component is degraded', () => {
    mockUseHealth.mockReturnValue({
      data: {
        status: 'healthy',
        components: {
          catalyst_pipeline: { status: 'degraded', details: 'Partial' },
        },
      },
      isSuccess: true,
    });
    const { result } = renderHook(() => usePipelineStatus(), { wrapper });
    expect(result.current).toBe(false);
  });
});

describe('catalyst hook gating', () => {
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

  it('does not fetch catalysts when pipeline is inactive', async () => {
    mockUseHealth.mockReturnValue({
      data: { status: 'healthy', components: {} },
      isSuccess: true,
    });

    const { result } = renderHook(() => useCatalystsBySymbol('AAPL'), { wrapper });

    // Wait a tick to ensure no fetch is triggered
    await new Promise((r) => setTimeout(r, 50));
    expect(mockFetch).not.toHaveBeenCalled();
    expect(result.current.isFetching).toBe(false);
  });

  it('fetches catalysts when pipeline is active', async () => {
    mockUseHealth.mockReturnValue({
      data: {
        status: 'healthy',
        components: {
          catalyst_pipeline: { status: 'healthy', details: 'Active' },
        },
      },
      isSuccess: true,
    });
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ catalysts: [], count: 0, symbol: 'AAPL' }),
    });

    const { result } = renderHook(() => useCatalystsBySymbol('AAPL'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('does not fetch recent catalysts when pipeline is inactive', async () => {
    mockUseHealth.mockReturnValue({
      data: { status: 'healthy', components: {} },
      isSuccess: true,
    });

    const { result } = renderHook(() => useRecentCatalysts(), { wrapper });

    await new Promise((r) => setTimeout(r, 50));
    expect(mockFetch).not.toHaveBeenCalled();
    expect(result.current.isFetching).toBe(false);
  });
});

describe('intelligence briefing hook gating', () => {
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

  it('does not fetch briefing when pipeline is inactive', async () => {
    mockUseHealth.mockReturnValue({
      data: { status: 'healthy', components: {} },
      isSuccess: true,
    });

    const { result } = renderHook(() => useIntelligenceBriefing(), { wrapper });

    await new Promise((r) => setTimeout(r, 50));
    expect(mockFetch).not.toHaveBeenCalled();
    expect(result.current.isFetching).toBe(false);
  });

  it('fetches briefing when pipeline is active', async () => {
    mockUseHealth.mockReturnValue({
      data: {
        status: 'healthy',
        components: {
          catalyst_pipeline: { status: 'healthy', details: 'Active' },
        },
      },
      isSuccess: true,
    });
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          date: '2026-03-12',
          brief_type: 'premarket',
          content: 'Test brief',
          symbols_covered: ['AAPL'],
          catalyst_count: 5,
          generated_at: '2026-03-12T08:00:00Z',
          generation_cost_usd: 0.05,
        }),
    });

    const { result } = renderHook(() => useIntelligenceBriefing(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('does not fetch briefing history when pipeline is inactive', async () => {
    mockUseHealth.mockReturnValue({
      data: { status: 'healthy', components: {} },
      isSuccess: true,
    });

    const { result } = renderHook(() => useIntelligenceBriefingHistory(), { wrapper });

    await new Promise((r) => setTimeout(r, 50));
    expect(mockFetch).not.toHaveBeenCalled();
    expect(result.current.isFetching).toBe(false);
  });
});
