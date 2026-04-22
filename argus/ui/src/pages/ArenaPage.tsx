/**
 * The Arena — real-time multi-chart position monitoring page.
 *
 * Edge-to-edge layout (negates AppShell padding).
 * Top strip: ArenaStatsBar (48px).
 * Below: ArenaControls sort/filter bar.
 * Remainder: responsive CSS grid of ArenaCards.
 *
 * Sprint 32.75, Session 10 (API wiring + card rendering).
 * Sprint 32.75, Session 11 (live WS data — ticks, candles, position add/remove, stats).
 * Sprint 32.75, Session 12 (AnimatePresence, priority sizing, disconnection overlay).
 */

import { useState, useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { LayoutGrid } from 'lucide-react';
import { ArenaStatsBar } from '../features/arena/ArenaStatsBar';
import { ArenaControls } from '../features/arena/ArenaControls';
import { ArenaCard } from '../features/arena';
import { useArenaWebSocket } from '../features/arena/useArenaWebSocket';
import { useArenaData, sortPositions, filterPositions } from '../hooks/useArenaData';
import type { ArenaSortMode } from '../features/arena/ArenaControls';
import {
  ARENA_PRIORITY_RECOMPUTE_MS,
  ARENA_PRIORITY_SPAN_THRESHOLD,
} from '../constants/arena';

export type { ArenaSortMode };

// ---------------------------------------------------------------------------
// Priority score computation
// ---------------------------------------------------------------------------

/**
 * Compute attention-weighted priority score (0–1) for a position card.
 *
 * Score is high when price is near stop (danger) or near T1 (opportunity).
 * Score is low when price is midway between entry and targets.
 *
 * @param currentPrice - Live price from WS tick or latest candle close.
 * @param entryPrice   - Position entry price.
 * @param stopPrice    - Stop-loss price.
 * @param t1Price      - First target price.
 * @returns Priority score in [0, 1]. Returns 0 for degenerate ranges.
 */
export function computePriorityScore(
  currentPrice: number,
  entryPrice: number,
  stopPrice: number,
  t1Price: number,
): number {
  if (entryPrice <= stopPrice || t1Price <= entryPrice) return 0;

  const clamp = (v: number) => Math.max(0, Math.min(1, v));
  const proximityToStop = clamp((currentPrice - stopPrice) / (entryPrice - stopPrice));
  const proximityToT1 = clamp((t1Price - currentPrice) / (t1Price - entryPrice));

  return 1 - Math.min(proximityToStop, proximityToT1);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ArenaPage() {
  const [sortMode, setSortMode] = useState<ArenaSortMode>('entry_time');
  const [strategyFilter, setStrategyFilter] = useState<string>('all');

  // REST layer: provides initial positions and historical candles per symbol.
  const { positions: initialPositions, candlesBySymbol, isLoading } = useArenaData();

  // WS layer: live position list, aggregate stats, tick overlays, chart dispatch.
  const { positions, stats, liveOverlays, wsStatus, registerChartRef } =
    useArenaWebSocket(initialPositions);

  // Priority spans: keyed by `${strategy_id}-${symbol}-${entry_time}`.
  // Recomputed every 2 seconds to avoid layout thrashing.
  const [prioritySpans, setPrioritySpans] = useState<Record<string, number>>({});
  const liveOverlaysRef = useRef(liveOverlays);
  liveOverlaysRef.current = liveOverlays;
  const positionsRef = useRef(positions);
  positionsRef.current = positions;
  const candlesBySymbolRef = useRef(candlesBySymbol);
  candlesBySymbolRef.current = candlesBySymbol;

  useEffect(() => {
    function recomputeSpans(): void {
      const isMobile = window.innerWidth < 640;
      const next: Record<string, number> = {};

      positionsRef.current.forEach((pos) => {
        const key = `${pos.strategy_id}-${pos.symbol}-${pos.entry_time}`;
        if (isMobile) {
          next[key] = 1;
          return;
        }
        const overlay = liveOverlaysRef.current[pos.symbol];
        const latestClose =
          candlesBySymbolRef.current[pos.symbol]?.slice(-1)[0]?.close ?? pos.entry_price;
        const currentPrice = overlay?.current_price ?? latestClose;
        const t1Price = pos.target_prices[0] ?? 0;
        const score = computePriorityScore(currentPrice, pos.entry_price, pos.stop_price, t1Price);
        next[key] = score > ARENA_PRIORITY_SPAN_THRESHOLD ? 2 : 1;
      });

      setPrioritySpans(next);
    }

    recomputeSpans();
    const intervalId = setInterval(recomputeSpans, ARENA_PRIORITY_RECOMPUTE_MS);
    return () => clearInterval(intervalId);
  }, []); // Stable: reads via refs to avoid stale closure

  const displayPositions = sortPositions(
    filterPositions(positions, strategyFilter),
    sortMode,
  );

  // When a specific strategy is filtered, compute stats from visible positions
  // rather than the WebSocket aggregate (which covers all positions).
  const filteredStats =
    strategyFilter !== 'all'
      ? {
          position_count: displayPositions.length,
          total_pnl: displayPositions.reduce((sum, pos) => {
            const overlay = liveOverlays[pos.symbol];
            return sum + (overlay?.unrealized_pnl ?? pos.unrealized_pnl);
          }, 0),
          net_r: displayPositions.reduce((sum, pos) => {
            const overlay = liveOverlays[pos.symbol];
            return sum + (overlay?.r_multiple ?? pos.r_multiple);
          }, 0),
          entries_5m: stats.entries_5m,
          exits_5m: stats.exits_5m,
        }
      : stats;

  const isDisconnected = wsStatus === 'disconnected' || wsStatus === 'error';

  return (
    <div
      className="-m-4 md:-m-5 min-[1024px]:-m-6 min-[1024px]:-mt-6 flex flex-col overflow-hidden h-[calc(100vh-0px)] min-[1024px]:h-[calc(100vh-0px)]"
      data-testid="arena-page"
    >
      {/* Top stats strip — 48px fixed height; uses filtered stats when filter is active */}
      <ArenaStatsBar
        positionCount={filteredStats.position_count}
        totalPnl={filteredStats.total_pnl}
        netR={filteredStats.net_r}
        entries5m={filteredStats.entries_5m}
        exits5m={filteredStats.exits_5m}
      />

      {/* Sort + filter controls */}
      <ArenaControls
        sortMode={sortMode}
        onSortChange={setSortMode}
        strategyFilter={strategyFilter}
        onFilterChange={setStrategyFilter}
      />

      {/* Grid or empty state */}
      <div className="relative flex-1 overflow-auto p-3 pb-24 min-[1024px]:pb-3">
        {/* Disconnection overlay banner */}
        {isDisconnected && (
          <div
            className="absolute inset-x-0 top-0 z-20 p-3"
            data-testid="arena-disconnect-overlay"
          >
            <div className="w-full bg-argus-surface/90 border border-argus-warning/50 text-argus-warning text-sm px-4 py-2 rounded-lg text-center pointer-events-none">
              Connection lost — reconnecting...
            </div>
          </div>
        )}

        {!isLoading && displayPositions.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center h-full gap-3 text-argus-text-dim"
            data-testid="arena-empty-state"
          >
            <LayoutGrid className="w-10 h-10 opacity-30" />
            <p className="text-sm">No open positions</p>
          </div>
        ) : (
          <div
            className="grid gap-3"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}
            data-testid="arena-grid"
          >
            <AnimatePresence mode="popLayout">
              {displayPositions.map((pos) => {
                const overlay = liveOverlays[pos.symbol];
                const pnl = overlay?.unrealized_pnl ?? pos.unrealized_pnl;
                const pnlPositive = pnl >= 0;
                const key = `${pos.strategy_id}-${pos.symbol}-${pos.entry_time}`;
                const span = prioritySpans[key] ?? 1;

                return (
                  <motion.div
                    key={key}
                    layout
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, transition: { duration: 0.5, delay: 0.3 } }}
                    transition={{ duration: 0.3, layout: { duration: 0.5 } }}
                    style={{
                      gridColumn: span > 1 ? 'span 2' : undefined,
                      position: 'relative',
                    }}
                    data-testid="arena-card-wrapper"
                  >
                    {/* Flash overlay — invisible at rest, flashes on exit */}
                    <motion.div
                      className="absolute inset-0 rounded-lg pointer-events-none z-10"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 0 }}
                      exit={{
                        opacity: [0, 0.15, 0],
                        transition: { duration: 0.8, times: [0, 0.375, 1] },
                      }}
                      style={{
                        backgroundColor: pnlPositive ? '#22c55e' : '#ef4444',
                      }}
                    />
                    <ArenaCard
                      symbol={pos.symbol}
                      strategy_id={pos.strategy_id}
                      pnl={pnl}
                      r_multiple={overlay?.r_multiple ?? pos.r_multiple}
                      currentPrice={overlay?.current_price}
                      hold_seconds={pos.hold_duration_seconds}
                      entry_price={pos.entry_price}
                      stop_price={pos.stop_price}
                      target_prices={pos.target_prices}
                      trailing_stop_price={
                        (overlay?.trailing_stop_price || pos.trailing_stop_price) || undefined
                      }
                      entry_time={pos.entry_time}
                      candles={candlesBySymbol[pos.symbol] ?? []}
                      onChartMount={registerChartRef}
                    />
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
