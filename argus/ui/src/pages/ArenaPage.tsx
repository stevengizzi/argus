/**
 * The Arena — real-time multi-chart position monitoring page.
 *
 * Edge-to-edge layout (negates AppShell padding).
 * Top strip: ArenaStatsBar (48px).
 * Below: ArenaControls sort/filter bar.
 * Remainder: responsive CSS grid of ArenaCards.
 *
 * API wiring and card population are handled in S10.
 * Animation layer added in S12.
 *
 * Sprint 32.75, Session 8.
 */

import { useState } from 'react';
import { LayoutGrid } from 'lucide-react';
import { ArenaStatsBar } from '../features/arena/ArenaStatsBar';
import { ArenaControls } from '../features/arena/ArenaControls';
import type { ArenaSortMode } from '../features/arena/ArenaControls';
import type { ArenaCardProps } from '../features/arena/ArenaCard';

export function ArenaPage() {
  const [sortMode, setSortMode] = useState<ArenaSortMode>('entry_time');
  const [strategyFilter, setStrategyFilter] = useState<string>('all');

  // Populated by S10 (API wiring). Empty shell until then.
  const positions: ArenaCardProps[] = [];

  return (
    <div
      className="-m-4 md:-m-5 min-[1024px]:-m-6 min-[1024px]:-mt-6 flex flex-col overflow-hidden h-[calc(100vh-0px)] min-[1024px]:h-[calc(100vh-0px)]"
      data-testid="arena-page"
    >
      {/* Top stats strip — 48px fixed height */}
      <ArenaStatsBar />

      {/* Sort + filter controls */}
      <ArenaControls
        sortMode={sortMode}
        onSortChange={setSortMode}
        strategyFilter={strategyFilter}
        onFilterChange={setStrategyFilter}
      />

      {/* Grid or empty state */}
      <div className="flex-1 overflow-auto p-3 pb-24 min-[1024px]:pb-3">
        {positions.length === 0 ? (
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
            {/* ArenaCard items rendered here in S10 */}
          </div>
        )}
      </div>
    </div>
  );
}
