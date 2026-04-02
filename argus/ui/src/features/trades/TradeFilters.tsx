/**
 * Trade filters component with controlled state.
 *
 * Provides: strategy dropdown, outcome toggle (wins/losses/breakeven), date range,
 * and quick date filter buttons (Today/Week/Month/All).
 * Parent component controls filter state; URL sync handled by parent.
 *
 * Updated with SegmentedTab for outcome filter (17-B).
 * Updated with quick date filter buttons (21.5.1 Session 4).
 */

import { useMemo, useCallback } from 'react';
import { X } from 'lucide-react';
import { SegmentedTab } from '../../components/SegmentedTab';
import { useStrategies } from '../../hooks/useStrategies';
import { useTrades } from '../../hooks/useTrades';
import {
  useTradeFiltersStore,
  computeDateRangeForQuickFilter,
  type QuickFilter,
} from '../../stores/tradeFilters';
import type { OutcomeFilter, TradeFilterValues } from '../../hooks/useTradeFilters';
import type { SegmentedTabSegment } from '../../components/SegmentedTab';

interface FilterState {
  strategy_id: string | undefined;
  outcome: OutcomeFilter;
  date_from: string | undefined;
  date_to: string | undefined;
}

interface TradeFiltersProps {
  filters: FilterState;
  onFiltersChange: (updates: Partial<TradeFilterValues>) => void;
}

export function TradeFilters({ filters, onFiltersChange }: TradeFiltersProps) {
  const { data: strategiesData } = useStrategies();
  const { quickFilter, setQuickFilter } = useTradeFiltersStore();

  // Fetch counts for each outcome (using broader filters minus outcome)
  // Using limit: 1 since we only need total_count
  const baseFilters = {
    strategy_id: filters.strategy_id,
    date_from: filters.date_from,
    date_to: filters.date_to,
    limit: 1,
  };

  const { data: allTradesData } = useTrades(baseFilters);
  const { data: winsData } = useTrades({ ...baseFilters, outcome: 'win' });
  const { data: lossesData } = useTrades({ ...baseFilters, outcome: 'loss' });
  const { data: beData } = useTrades({ ...baseFilters, outcome: 'breakeven' });

  const { strategy_id, outcome, date_from, date_to } = filters;

  // Handle quick filter button click
  const handleQuickFilter = useCallback(
    (label: QuickFilter) => {
      setQuickFilter(label);
      const { dateFrom, dateTo } = computeDateRangeForQuickFilter(label);
      onFiltersChange({ date_from: dateFrom, date_to: dateTo });
    },
    [setQuickFilter, onFiltersChange]
  );

  // Check if any filters are active
  const hasActiveFilters = Boolean(
    strategy_id || outcome !== 'all' || date_from || date_to
  );

  // Clear all filters
  const handleClearFilters = useCallback(() => {
    setQuickFilter('all');
    onFiltersChange({
      strategy_id: undefined,
      outcome: 'all',
      date_from: undefined,
      date_to: undefined,
    });
  }, [setQuickFilter, onFiltersChange]);

  // Build segments with live counts
  const outcomeSegments: SegmentedTabSegment[] = useMemo(() => [
    {
      label: 'All',
      value: 'all',
      count: allTradesData?.total_count,
    },
    {
      label: 'Wins',
      value: 'win',
      count: winsData?.total_count,
      countVariant: 'success' as const,
    },
    {
      label: 'Losses',
      value: 'loss',
      count: lossesData?.total_count,
      countVariant: 'danger' as const,
    },
    {
      label: 'BE',
      value: 'breakeven',
      count: beData?.total_count,
    },
  ], [allTradesData?.total_count, winsData?.total_count, lossesData?.total_count, beData?.total_count]);

  return (
    <div className="bg-argus-surface-2/50 border border-argus-border rounded-lg px-4 py-2 flex flex-wrap items-center gap-2">
      {/* Strategy dropdown */}
      <select
        value={strategy_id || ''}
        onChange={(e) => onFiltersChange({ strategy_id: e.target.value || undefined })}
        className="h-8 bg-argus-surface-2 border border-argus-border rounded-md px-3 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
      >
        <option value="">All Strategies</option>
        {strategiesData?.strategies.map((s) => (
          <option key={s.strategy_id} value={s.strategy_id}>
            {s.name}
          </option>
        ))}
      </select>

      {/* Outcome segmented tab */}
      <SegmentedTab
        segments={outcomeSegments}
        activeValue={outcome}
        onChange={(value) => onFiltersChange({ outcome: value as OutcomeFilter })}
        size="sm"
        layoutId="trade-outcome-filter"
      />

      {/* Time preset buttons */}
      {(['today', 'week', 'month', 'all'] as const).map((label) => (
        <button
          key={label}
          onClick={() => handleQuickFilter(label)}
          className={`h-8 px-3 text-xs rounded transition-colors ${
            quickFilter === label
              ? 'bg-argus-accent text-white'
              : 'bg-argus-surface-2 text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-3'
          }`}
          data-testid={`quick-filter-${label}`}
        >
          {label === 'today' ? 'Today' : label === 'week' ? 'Week' : label === 'month' ? 'Month' : 'All'}
        </button>
      ))}

      {/* Date range */}
      <input
        type="date"
        aria-label="From date"
        value={date_from || ''}
        onChange={(e) => {
          const newFrom = e.target.value || undefined;
          setQuickFilter('all');
          if (newFrom && date_to && newFrom > date_to) {
            onFiltersChange({ date_from: newFrom, date_to: undefined });
          } else {
            onFiltersChange({ date_from: newFrom });
          }
        }}
        className="h-8 bg-argus-surface-2 border border-argus-border rounded-md px-3 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
      />
      <input
        type="date"
        aria-label="To date"
        value={date_to || ''}
        min={date_from || ''}
        onChange={(e) => {
          const newTo = e.target.value || undefined;
          setQuickFilter('all');
          if (newTo && date_from && newTo < date_from) {
            return;
          }
          onFiltersChange({ date_to: newTo });
        }}
        className="h-8 bg-argus-surface-2 border border-argus-border rounded-md px-3 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
      />

      {/* Clear all filters button */}
      {hasActiveFilters && (
        <button
          onClick={handleClearFilters}
          className="h-8 flex items-center gap-1 px-2 text-xs text-argus-text-dim hover:text-argus-text transition-colors"
          title="Clear all filters"
        >
          <X className="w-3 h-3" />
          Clear
        </button>
      )}
    </div>
  );
}
