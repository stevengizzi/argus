/**
 * Tests for useArenaWebSocket hook.
 *
 * Sprint 32.75, Session 11.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import type { ArenaPosition } from '../../api/types';
import type { MiniChartHandle } from './MiniChart';

// ---------------------------------------------------------------------------
// Mock getToken
// ---------------------------------------------------------------------------
vi.mock('../../api/client', () => ({
  getToken: () => 'test-token',
}));

// ---------------------------------------------------------------------------
// WebSocket mock infrastructure
// ---------------------------------------------------------------------------

interface MockWsInstance {
  onopen: (() => void) | null;
  onmessage: ((event: { data: string }) => void) | null;
  onclose: (() => void) | null;
  close: ReturnType<typeof vi.fn>;
  send: ReturnType<typeof vi.fn>;
}

let wsInstance: MockWsInstance | null = null;

// Must be a regular function (not arrow) so `new MockWebSocket(...)` works.
const MockWebSocket = vi.fn(function MockWebSocketConstructor() {
  wsInstance = {
    onopen: null,
    onmessage: null,
    onclose: null,
    close: vi.fn(),
    send: vi.fn(),
  };
  return wsInstance;
});

// Synchronous rAF — runs callback immediately so we don't need fake timers.
vi.stubGlobal('requestAnimationFrame', vi.fn((cb: FrameRequestCallback) => {
  cb(0);
  return 0;
}));
vi.stubGlobal('cancelAnimationFrame', vi.fn());

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const EMPTY_POSITIONS: ArenaPosition[] = [];

const OPEN_POSITION: ArenaPosition = {
  symbol: 'AAPL',
  strategy_id: 'orb_breakout',
  side: 'long',
  shares: 100,
  entry_price: 175,
  current_price: 178,
  stop_price: 170,
  target_prices: [182],
  trailing_stop_price: null,
  unrealized_pnl: 300,
  r_multiple: 0.6,
  hold_duration_seconds: 300,
  quality_grade: 'B',
  entry_time: '2024-01-15T09:30:00Z',
};

function makeMiniChartHandle(): MiniChartHandle {
  return {
    updateCandle: vi.fn(),
    appendCandle: vi.fn(),
    updateTrailingStop: vi.fn(),
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function sendMessage(msg: Record<string, unknown>): void {
  wsInstance!.onmessage!({ data: JSON.stringify(msg) });
}

function connectAndAuth(): void {
  wsInstance!.onopen!();
  sendMessage({ type: 'auth_success' });
}

// ---------------------------------------------------------------------------
// Import hook after mocks are set up
// ---------------------------------------------------------------------------
const { useArenaWebSocket } = await import('./useArenaWebSocket');

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useArenaWebSocket', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.clearAllMocks();
    wsInstance = null;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    // Restore rAF stubs removed by unstubAllGlobals
    vi.stubGlobal('requestAnimationFrame', vi.fn((cb: FrameRequestCallback) => { cb(0); return 0; }));
    vi.stubGlobal('cancelAnimationFrame', vi.fn());
  });

  it('connects to /ws/v1/arena and sends auth token on open', () => {
    renderHook(() => useArenaWebSocket(EMPTY_POSITIONS));

    expect(MockWebSocket).toHaveBeenCalledWith(
      expect.stringContaining('/ws/v1/arena'),
    );

    act(() => {
      wsInstance!.onopen!();
    });

    expect(wsInstance!.send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'auth', token: 'test-token' }),
    );
  });

  it('dispatches tick to correct chart ref and updates live overlay', () => {
    const { result } = renderHook(() => useArenaWebSocket(EMPTY_POSITIONS));
    const handle = makeMiniChartHandle();

    act(() => {
      connectAndAuth();
      result.current.registerChartRef('NVDA', handle);
      sendMessage({
        type: 'arena_tick',
        symbol: 'NVDA',
        price: 880.0,
        unrealized_pnl: 250.0,
        r_multiple: 1.2,
        trailing_stop_price: 870.0,
      });
    });

    expect(handle.updateCandle).toHaveBeenCalledWith(
      expect.objectContaining({ close: 880.0 }),
    );
    expect(handle.updateTrailingStop).toHaveBeenCalledWith(870.0);
    expect(result.current.liveOverlays['NVDA']).toMatchObject({
      unrealized_pnl: 250.0,
      r_multiple: 1.2,
      current_price: 880.0,
      trailing_stop_price: 870.0,
    });
  });

  it('creates forming candle on first tick and accumulates high/low on subsequent ticks', () => {
    const { result } = renderHook(() => useArenaWebSocket(EMPTY_POSITIONS));
    const handle = makeMiniChartHandle();

    act(() => {
      connectAndAuth();
      result.current.registerChartRef('TSLA', handle);
      sendMessage({ type: 'arena_tick', symbol: 'TSLA', price: 200, unrealized_pnl: 0, r_multiple: 0, trailing_stop_price: 0 });
    });

    const first = (handle.updateCandle as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(first).toMatchObject({ open: 200, high: 200, low: 200, close: 200 });

    act(() => {
      sendMessage({ type: 'arena_tick', symbol: 'TSLA', price: 205, unrealized_pnl: 0, r_multiple: 0, trailing_stop_price: 0 });
    });
    const second = (handle.updateCandle as ReturnType<typeof vi.fn>).mock.calls[1][0];
    expect(second).toMatchObject({ open: 200, high: 205, low: 200, close: 205 });

    act(() => {
      sendMessage({ type: 'arena_tick', symbol: 'TSLA', price: 198, unrealized_pnl: 0, r_multiple: 0, trailing_stop_price: 0 });
    });
    const third = (handle.updateCandle as ReturnType<typeof vi.fn>).mock.calls[2][0];
    expect(third).toMatchObject({ open: 200, high: 205, low: 198, close: 198 });
  });

  it('calls appendCandle on arena_candle and clears forming candle slot', () => {
    const { result } = renderHook(() => useArenaWebSocket(EMPTY_POSITIONS));
    const handle = makeMiniChartHandle();

    act(() => {
      connectAndAuth();
      result.current.registerChartRef('MSFT', handle);
      // Tick to create a forming candle
      sendMessage({ type: 'arena_tick', symbol: 'MSFT', price: 420, unrealized_pnl: 0, r_multiple: 0, trailing_stop_price: 0 });
    });

    act(() => {
      sendMessage({
        type: 'arena_candle',
        symbol: 'MSFT',
        time: '2024-01-15T14:30:00Z',
        open: 418,
        high: 425,
        low: 417,
        close: 423,
        volume: 5000,
      });
    });

    expect(handle.appendCandle).toHaveBeenCalledWith(
      expect.objectContaining({ open: 418, high: 425, low: 417, close: 423 }),
    );
  });

  it('updates stats on arena_stats message', () => {
    const { result } = renderHook(() => useArenaWebSocket(EMPTY_POSITIONS));

    act(() => {
      connectAndAuth();
      sendMessage({
        type: 'arena_stats',
        position_count: 4,
        total_pnl: 875.50,
        net_r: 1.8,
        entries_5m: 2,
        exits_5m: 1,
      });
    });

    expect(result.current.stats).toMatchObject({
      position_count: 4,
      total_pnl: 875.50,
      net_r: 1.8,
      entries_5m: 2,
      exits_5m: 1,
    });
  });

  it('adds position on arena_position_opened', () => {
    const { result } = renderHook(() => useArenaWebSocket(EMPTY_POSITIONS));

    act(() => {
      connectAndAuth();
      sendMessage({
        type: 'arena_position_opened',
        symbol: 'AAPL',
        strategy_id: 'orb_breakout',
        entry_price: 175,
        stop_price: 170,
        target_prices: [180, 185],
        side: 'long',
        shares: 50,
        entry_time: '2024-01-15T09:31:00Z',
      });
    });

    expect(result.current.positions).toHaveLength(1);
    expect(result.current.positions[0]).toMatchObject({
      symbol: 'AAPL',
      strategy_id: 'orb_breakout',
      entry_price: 175,
      stop_price: 170,
    });
  });

  it('does not duplicate position if arena_position_opened fires twice for same symbol+strategy', () => {
    const { result } = renderHook(() => useArenaWebSocket(EMPTY_POSITIONS));
    const openedMsg = {
      type: 'arena_position_opened',
      symbol: 'AAPL',
      strategy_id: 'orb_breakout',
      entry_price: 175,
      stop_price: 170,
      target_prices: [180],
      side: 'long',
      shares: 50,
      entry_time: '2024-01-15T09:31:00Z',
    };

    act(() => {
      connectAndAuth();
      sendMessage(openedMsg);
      sendMessage(openedMsg);
    });

    expect(result.current.positions).toHaveLength(1);
  });

  it('removes position on arena_position_closed', () => {
    const { result } = renderHook(() => useArenaWebSocket([OPEN_POSITION]));

    act(() => {
      connectAndAuth();
      sendMessage({
        type: 'arena_position_closed',
        symbol: 'AAPL',
        strategy_id: 'orb_breakout',
        exit_price: 182,
        pnl: 700,
        r_multiple: 1.4,
        exit_reason: 'target_1',
      });
    });

    expect(result.current.positions).toHaveLength(0);
  });

  it('clears live overlay on arena_position_closed', () => {
    const { result } = renderHook(() => useArenaWebSocket([OPEN_POSITION]));
    const handle = makeMiniChartHandle();

    act(() => {
      connectAndAuth();
      result.current.registerChartRef('AAPL', handle);
      sendMessage({ type: 'arena_tick', symbol: 'AAPL', price: 180, unrealized_pnl: 500, r_multiple: 1.0, trailing_stop_price: 0 });
    });

    expect(result.current.liveOverlays['AAPL']).toBeDefined();

    act(() => {
      sendMessage({
        type: 'arena_position_closed',
        symbol: 'AAPL',
        strategy_id: 'orb_breakout',
        exit_price: 182,
        pnl: 700,
        r_multiple: 1.4,
        exit_reason: 'target_1',
      });
    });

    expect(result.current.liveOverlays['AAPL']).toBeUndefined();
  });

  it('unregistering a chart ref removes it from the dispatch map', () => {
    const { result } = renderHook(() => useArenaWebSocket(EMPTY_POSITIONS));
    const handle = makeMiniChartHandle();

    act(() => {
      connectAndAuth();
      result.current.registerChartRef('AAPL', handle);
      result.current.registerChartRef('AAPL', null);
      sendMessage({ type: 'arena_tick', symbol: 'AAPL', price: 180, unrealized_pnl: 0, r_multiple: 0, trailing_stop_price: 0 });
    });

    expect(handle.updateCandle).not.toHaveBeenCalled();
  });

  it('closes WebSocket on unmount', () => {
    const { unmount } = renderHook(() => useArenaWebSocket(EMPTY_POSITIONS));
    unmount();
    expect(wsInstance!.close).toHaveBeenCalled();
  });
});
