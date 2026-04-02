/**
 * The Arena — real-time multi-chart position monitoring page.
 *
 * Edge-to-edge layout (negates AppShell padding).
 * Top strip: ArenaStatsBar (48px).
 * Below: ArenaControls sort/filter bar.
 * Remainder: responsive CSS grid of ArenaCards.
 *
 * Sprint 32.75, Session 10 (API wiring + card rendering).
 * Animation layer added in S12.
 */

import { useState } from 'react';
import { LayoutGrid } from 'lucide-react';
import { ArenaStatsBar } from '../features/arena/ArenaStatsBar';
import { ArenaControls } from '../features/arena/ArenaControls';
import { ArenaCard } from '../features/arena/ArenaCard';
import { useArenaData, sortPositions, filterPositions } from '../hooks/useArenaData';
import type { ArenaSortMode } from '../features/arena/ArenaControls';

export function ArenaPage() {
  const [sortMode, setSortMode] = useState<ArenaSortMode>('entry_time');
  const [strategyFilter, setStrategyFilter] = useState<string>('all');

  const { positions, candlesBySymbol, isLoading, stats } = useArenaData();

  const displayPositions = sortPositions(
    filterPositions(positions, strategyFilter),
    sortMode,
  );

  return (
    <div
      className="-m-4 md:-m-5 min-[1024px]:-m-6 min-[1024px]:-mt-6 flex flex-col overflow-hidden h-[calc(100vh-0px)] min-[1024px]:h-[calc(100vh-0px)]"
      data-testid="arena-page"
    >
      {/* Top stats strip — 48px fixed height */}
      <ArenaStatsBar
        positionCount={stats.position_count}
        totalPnl={stats.total_pnl}
        netR={stats.net_r}
      />

      {/* Sort + filter controls */}
      <ArenaControls
        sortMode={sortMode}
        onSortChange={setSortMode}
        strategyFilter={strategyFilter}
        onFilterChange={setStrategyFilter}
      />

      {/* Grid or empty state */}
      <div className="flex-1 overflow-auto p-3 pb-24 min-[1024px]:pb-3">
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
            {displayPositions.map((pos) => (
              <ArenaCard
                key={`${pos.strategy_id}-${pos.symbol}-${pos.entry_time}`}
                symbol={pos.symbol}
                strategy_id={pos.strategy_id}
                pnl={pos.unrealized_pnl}
                r_multiple={pos.r_multiple}
                hold_seconds={pos.hold_duration_seconds}
                entry_price={pos.entry_price}
                stop_price={pos.stop_price}
                target_prices={pos.target_prices}
                trailing_stop_price={pos.trailing_stop_price ?? undefined}
                candles={candlesBySymbol[pos.symbol] ?? []}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
