/**
 * useArenaWebSocket: live Arena WebSocket hook.
 *
 * Connects to /ws/v1/arena, drives chart updates via MiniChart imperative
 * handles, and maintains live position state and aggregate stats.
 *
 * Sprint 32.75, Session 11.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import type { UTCTimestamp } from 'lightweight-charts';
import { getToken } from '../../api/client';
import type { ArenaPosition } from '../../api/types';
import type { MiniChartHandle, CandleData } from './MiniChart';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/** Real-time tick overlay: updates pnl, R-multiple, current price, trail stop. */
export interface LiveOverlay {
  unrealized_pnl: number;
  r_multiple: number;
  current_price: number;
  trailing_stop_price: number;
}

/** Stats message fields (superset of ArenaStats — includes 5-minute counters). */
export interface LiveArenaStats {
  position_count: number;
  total_pnl: number;
  net_r: number;
  entries_5m: number;
  exits_5m: number;
}

export type WsStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface UseArenaWebSocketResult {
  positions: ArenaPosition[];
  stats: LiveArenaStats;
  liveOverlays: Record<string, LiveOverlay>;
  wsStatus: WsStatus;
  registerChartRef: (symbol: string, handle: MiniChartHandle | null) => void;
}

// ---------------------------------------------------------------------------
// Internal types
// ---------------------------------------------------------------------------

interface TickBatch {
  price: number;
  unrealized_pnl: number;
  r_multiple: number;
  trailing_stop_price: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DEFAULT_STATS: LiveArenaStats = {
  position_count: 0,
  total_pnl: 0,
  net_r: 0,
  entries_5m: 0,
  exits_5m: 0,
};

/** Floor Date.now() to the current minute boundary, as a UTC timestamp in seconds. */
function currentMinuteTimestamp(): UTCTimestamp {
  return (Math.floor(Date.now() / 60_000) * 60) as UTCTimestamp;
}

/** Build an ArenaPosition stub from an arena_position_opened WS message. */
function buildPositionFromOpenedMsg(msg: Record<string, unknown>): ArenaPosition {
  return {
    symbol: msg.symbol as string,
    strategy_id: msg.strategy_id as string,
    side: (msg.side as string) ?? 'long',
    shares: (msg.shares as number) ?? 0,
    entry_price: msg.entry_price as number,
    current_price: msg.entry_price as number,
    stop_price: msg.stop_price as number,
    target_prices: (msg.target_prices as number[]) ?? [],
    trailing_stop_price: null,
    unrealized_pnl: 0,
    r_multiple: 0,
    hold_duration_seconds: 0,
    quality_grade: '',
    entry_time: (msg.entry_time as string) ?? new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useArenaWebSocket(initialPositions: ArenaPosition[]): UseArenaWebSocketResult {
  const [positions, setPositions] = useState<ArenaPosition[]>(initialPositions);
  const [stats, setStats] = useState<LiveArenaStats>(DEFAULT_STATS);
  const [liveOverlays, setLiveOverlays] = useState<Record<string, LiveOverlay>>({});
  const [wsStatus, setWsStatus] = useState<WsStatus>('connecting');

  // True once auth_success is received; prevents REST refetches from clobbering
  // WS-managed position state.
  const wsConnectedRef = useRef(false);

  // Chart handle registry: symbol → MiniChartHandle
  const chartRefsRef = useRef<Map<string, MiniChartHandle>>(new Map());

  // Forming (in-progress) candle per symbol for sub-candle live updates.
  const formingCandlesRef = useRef<Map<string, CandleData>>(new Map());

  // rAF batching: collect all ticks that arrive within a single frame.
  const rafPendingRef = useRef<Map<string, TickBatch>>(new Map());
  // Boolean guard prevents double-scheduling; numeric id needed for cleanup.
  const rafScheduledRef = useRef(false);
  const rafIdRef = useRef<number | null>(null);

  // Sync REST initial positions until WS takes over position state.
  useEffect(() => {
    if (!wsConnectedRef.current) {
      setPositions(initialPositions);
    }
  }, [initialPositions]);

  /** Register or deregister a MiniChart imperative handle for a symbol. */
  const registerChartRef = useCallback(
    (symbol: string, handle: MiniChartHandle | null) => {
      if (handle) {
        chartRefsRef.current.set(symbol, handle);
      } else {
        chartRefsRef.current.delete(symbol);
        formingCandlesRef.current.delete(symbol);
      }
    },
    [],
  );

  useEffect(() => {
    // -----------------------------------------------------------------------
    // rAF flush: apply all pending tick updates in one animation frame.
    // -----------------------------------------------------------------------
    function flushRaf(): void {
      rafScheduledRef.current = false;
      const pending = rafPendingRef.current;
      if (pending.size === 0) return;

      const overlayUpdates: Record<string, LiveOverlay> = {};

      pending.forEach((tick, symbol) => {
        const nowMinute = currentMinuteTimestamp();
        const existing = formingCandlesRef.current.get(symbol);

        // Create or extend the in-progress candle for the current minute.
        const forming: CandleData =
          !existing || existing.time !== nowMinute
            ? {
                time: nowMinute,
                open: tick.price,
                high: tick.price,
                low: tick.price,
                close: tick.price,
              }
            : {
                time: nowMinute,
                open: existing.open,
                high: Math.max(existing.high, tick.price),
                low: Math.min(existing.low, tick.price),
                close: tick.price,
              };

        formingCandlesRef.current.set(symbol, forming);

        const chartRef = chartRefsRef.current.get(symbol);
        if (chartRef) {
          chartRef.updateCandle(forming);
          if (tick.trailing_stop_price > 0) {
            chartRef.updateTrailingStop(tick.trailing_stop_price);
          }
        }

        overlayUpdates[symbol] = {
          unrealized_pnl: tick.unrealized_pnl,
          r_multiple: tick.r_multiple,
          current_price: tick.price,
          trailing_stop_price: tick.trailing_stop_price,
        };
      });

      pending.clear();
      setLiveOverlays((prev) => ({ ...prev, ...overlayUpdates }));
    }

    function scheduleRaf(): void {
      if (rafScheduledRef.current) return;
      rafScheduledRef.current = true;
      rafIdRef.current = requestAnimationFrame(flushRaf);
    }

    // -----------------------------------------------------------------------
    // WebSocket connection
    // -----------------------------------------------------------------------
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/ws/v1/arena`);

    ws.onopen = () => {
      const token = getToken();
      if (!token) {
        ws.close();
        return;
      }
      ws.send(JSON.stringify({ type: 'auth', token }));
    };

    ws.onmessage = (event: MessageEvent<string>) => {
      let msg: Record<string, unknown>;
      try {
        msg = JSON.parse(event.data) as Record<string, unknown>;
      } catch {
        return;
      }

      switch (msg.type) {
        case 'auth_success': {
          wsConnectedRef.current = true;
          setWsStatus('connected');
          break;
        }

        case 'arena_tick': {
          rafPendingRef.current.set(msg.symbol as string, {
            price: msg.price as number,
            unrealized_pnl: msg.unrealized_pnl as number,
            r_multiple: msg.r_multiple as number,
            trailing_stop_price: (msg.trailing_stop_price as number) ?? 0,
          });
          scheduleRaf();
          break;
        }

        case 'arena_candle': {
          const symbol = msg.symbol as string;
          const time = (new Date(msg.time as string).getTime() / 1000) as UTCTimestamp;
          const candle: CandleData = {
            time,
            open: msg.open as number,
            high: msg.high as number,
            low: msg.low as number,
            close: msg.close as number,
          };
          // Completed candle locks the forming candle slot.
          formingCandlesRef.current.delete(symbol);
          chartRefsRef.current.get(symbol)?.appendCandle(candle);
          break;
        }

        case 'arena_position_opened': {
          const opened = buildPositionFromOpenedMsg(msg);
          setPositions((prev) => {
            const exists = prev.some(
              (p) => p.symbol === opened.symbol && p.strategy_id === opened.strategy_id,
            );
            return exists ? prev : [...prev, opened];
          });
          break;
        }

        case 'arena_position_closed': {
          const symbol = msg.symbol as string;
          const strategyId = msg.strategy_id as string;
          setPositions((prev) =>
            prev.filter(
              (p) => !(p.symbol === symbol && p.strategy_id === strategyId),
            ),
          );
          setLiveOverlays((prev) => {
            const next = { ...prev };
            delete next[symbol];
            return next;
          });
          formingCandlesRef.current.delete(symbol);
          break;
        }

        case 'arena_stats': {
          setStats({
            position_count: msg.position_count as number,
            total_pnl: msg.total_pnl as number,
            net_r: msg.net_r as number,
            entries_5m: msg.entries_5m as number,
            exits_5m: msg.exits_5m as number,
          });
          break;
        }

        default:
          break;
      }
    };

    ws.onerror = () => {
      setWsStatus('error');
    };

    ws.onclose = () => {
      wsConnectedRef.current = false;
      setWsStatus('disconnected');
    };

    return () => {
      ws.close();
      if (rafScheduledRef.current && rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
        rafScheduledRef.current = false;
      }
      wsConnectedRef.current = false;
    };
  }, []); // Run once on mount — WS lifecycle tied to component lifetime.

  return { positions, stats, liveOverlays, wsStatus, registerChartRef };
}
