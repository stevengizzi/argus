/**
 * ArenaControls — sort and filter bar for The Arena page.
 *
 * Sort mode: Entry Time | Strategy | P&L | Urgency.
 * Strategy filter: All + each of the 12 active strategies with their color dots.
 *
 * Purely presentational — state is lifted to ArenaPage.
 *
 * Sprint 32.75, Session 8.
 */

import { STRATEGY_DISPLAY } from '../../utils/strategyConfig';

export type ArenaSortMode = 'entry_time' | 'strategy' | 'pnl' | 'urgency';

const SORT_OPTIONS: Array<{ value: ArenaSortMode; label: string }> = [
  { value: 'entry_time', label: 'Entry Time' },
  { value: 'strategy', label: 'Strategy' },
  { value: 'pnl', label: 'P&L' },
  { value: 'urgency', label: 'Urgency' },
];

export interface ArenaControlsProps {
  sortMode: ArenaSortMode;
  onSortChange: (mode: ArenaSortMode) => void;
  strategyFilter: string;
  onFilterChange: (strategyId: string) => void;
}

const selectClass =
  'bg-argus-surface-2 border border-argus-border rounded text-xs text-argus-text ' +
  'px-2 py-1 focus:outline-none focus:border-argus-accent cursor-pointer';

export function ArenaControls({
  sortMode,
  onSortChange,
  strategyFilter,
  onFilterChange,
}: ArenaControlsProps) {
  return (
    <div
      className="flex items-center gap-4 px-3 py-2 bg-argus-surface border-b border-argus-border flex-none"
      data-testid="arena-controls"
    >
      {/* Sort mode */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-argus-text-dim uppercase tracking-widest">Sort</span>
        <select
          value={sortMode}
          onChange={(e) => onSortChange(e.target.value as ArenaSortMode)}
          className={selectClass}
          data-testid="sort-mode-select"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Strategy filter */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-argus-text-dim uppercase tracking-widest">Strategy</span>
        <select
          value={strategyFilter}
          onChange={(e) => onFilterChange(e.target.value)}
          className={selectClass}
          data-testid="strategy-filter-select"
        >
          <option value="all">All</option>
          {Object.entries(STRATEGY_DISPLAY).map(([id, config]) => (
            <option key={id} value={id}>
              {config.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
