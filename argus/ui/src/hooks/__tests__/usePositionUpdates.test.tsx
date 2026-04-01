/**
 * Tests for usePositionUpdates hook.
 *
 * Sprint 29.5 Session 4.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import type { MessageHandler } from '../../api/ws';
import type { PositionsResponse, WebSocketMessage } from '../../api/types';

// Capture the message handler registered by the hook
let capturedHandler: MessageHandler | null = null;
const mockUnsubscribe = vi.fn();

vi.mock('../../api/ws', () => ({
  getWebSocketClient: () => ({
    onMessage: (handler: MessageHandler) => {
      capturedHandler = handler;
      return mockUnsubscribe;
    },
  }),
}));

const { usePositionUpdates } = await import('../usePositionUpdates');

function makePositionsResponse(overrides?: Partial<PositionsResponse>): PositionsResponse {
  return {
    positions: [
      {
        position_id: 'pos-001',
        strategy_id: 'strat_orb_breakout',
        symbol: 'TSLA',
        side: 'long',
        entry_price: 250.0,
        entry_time: '2026-03-31T14:00:00Z',
        shares_total: 100,
        shares_remaining: 100,
        current_price: 252.0,
        unrealized_pnl: 200.0,
        unrealized_pnl_pct: 0.8,
        stop_price: 248.0,
        t1_price: 254.0,
        t2_price: 258.0,
        t1_filled: false,
        hold_duration_seconds: 300,
        r_multiple_current: 1.0,
      },
    ],
    count: 1,
    timestamp: '2026-03-31T14:00:00Z',
    ...overrides,
  };
}

function makeWsMessage(data: Record<string, unknown>): WebSocketMessage {
  return {
    type: 'position.updated',
    data,
    sequence: 1,
    timestamp: '2026-03-31T14:01:00Z',
  };
}

describe('usePositionUpdates', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    capturedHandler = null;
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  afterEach(() => {
    queryClient.clear();
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('merges position.updated into the query cache', () => {
    // Seed the cache with initial positions data
    queryClient.setQueryData(['positions', undefined], makePositionsResponse());

    renderHook(() => usePositionUpdates(), { wrapper });

    expect(capturedHandler).not.toBeNull();

    // Simulate a WS message
    act(() => {
      capturedHandler!(makeWsMessage({
        symbol: 'TSLA',
        current_price: 255.0,
        unrealized_pnl: 500.0,
        r_multiple: 2.5,
        position_id: 'pos-001',
        strategy_id: 'strat_orb_breakout',
        entry_price: 250.0,
        shares: 100,
        stop_updated_to: null,
      }));
    });

    const cached = queryClient.getQueryData<PositionsResponse>(['positions', undefined]);
    expect(cached).toBeDefined();
    const pos = cached!.positions[0];
    expect(pos.current_price).toBe(255.0);
    expect(pos.unrealized_pnl).toBe(500.0);
    expect(pos.r_multiple_current).toBe(2.5);
    // Fields not in the update remain unchanged
    expect(pos.entry_price).toBe(250.0);
    expect(pos.stop_price).toBe(248.0);
  });

  it('ignores updates for symbols not in the positions list', () => {
    const original = makePositionsResponse();
    queryClient.setQueryData(['positions', undefined], original);

    renderHook(() => usePositionUpdates(), { wrapper });

    act(() => {
      capturedHandler!(makeWsMessage({
        symbol: 'NVDA',
        current_price: 900.0,
        unrealized_pnl: 1000.0,
        r_multiple: 3.0,
        position_id: 'pos-999',
        strategy_id: 'strat_orb_breakout',
        entry_price: 870.0,
        shares: 50,
        stop_updated_to: null,
      }));
    });

    const cached = queryClient.getQueryData<PositionsResponse>(['positions', undefined]);
    // Positions unchanged — same reference since no match triggers identity return
    expect(cached!.positions[0].current_price).toBe(252.0);
  });

  it('ignores non position.updated message types', () => {
    queryClient.setQueryData(['positions', undefined], makePositionsResponse());

    renderHook(() => usePositionUpdates(), { wrapper });

    act(() => {
      capturedHandler!({
        type: 'position.opened',
        data: { symbol: 'TSLA', current_price: 999.0 },
        sequence: 2,
        timestamp: '2026-03-31T14:02:00Z',
      });
    });

    const cached = queryClient.getQueryData<PositionsResponse>(['positions', undefined]);
    expect(cached!.positions[0].current_price).toBe(252.0);
  });

  it('unsubscribes from WS on unmount', () => {
    const { unmount } = renderHook(() => usePositionUpdates(), { wrapper });

    unmount();

    expect(mockUnsubscribe).toHaveBeenCalledOnce();
  });
});

describe('usePositions refetchInterval', () => {
  it('uses 15s polling interval as REST backstop', async () => {
    const { usePositions } = await import('../usePositions');

    // Inspect the hook's query options by rendering it with a mock fetch
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ positions: [], count: 0, timestamp: '' }),
    });
    global.fetch = mockFetch;

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const w = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => usePositions(), { wrapper: w });

    // The query should exist with a 15s refetch interval
    const queryState = qc.getQueryCache().findAll({ queryKey: ['positions'] });
    expect(queryState.length).toBeGreaterThan(0);
    // Verify the observer has the correct interval
    const observer = queryState[0];
    expect(observer.options.refetchInterval).toBe(15_000);

    qc.clear();
  });
});
