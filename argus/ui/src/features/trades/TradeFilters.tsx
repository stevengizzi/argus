/**
 * Trade filters component with controlled state.
 *
 * Provides: strategy dropdown, outcome toggle (wins/losses/breakeven), date range.
 * Parent component controls filter state; URL sync handled by parent.
 *
 * Updated with SegmentedTab for outcome filter (17-B).
 */

import { useMemo } from 'react';
import { SegmentedTab } from '../../components/SegmentedTab';
import { useStrategies } from '../../hooks/useStrategies';
import { useTrades } from '../../hooks/useTrades';
import type { OutcomeFilter, TradeFilterValues } from '../../hooks/useTradeFilters';
import type { SegmentedTabSegment } from '../../components/SegmentedTab';

interface FilterState {
  strategy_id: string | undefined;
  outcome: OutcomeFilter;
  date_from: string | undefined;
  date_to: string | undefined;
  page: number;
}

interface TradeFiltersProps {
  filters: FilterState;
  onFiltersChange: (updates: Partial<TradeFilterValues>) => void;
}

export function TradeFilters({ filters, onFiltersChange }: TradeFiltersProps) {
  const { data: strategiesData } = useStrategies();

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
    <div className="bg-argus-surface border border-argus-border rounded-lg p-3 md:p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:gap-4">
        {/* Strategy dropdown */}
        <div className="flex-1 min-w-0 lg:max-w-[200px]">
          <label className="block text-xs text-argus-text-dim uppercase tracking-wide mb-1">
            Strategy
          </label>
          <select
            value={strategy_id || ''}
            onChange={(e) => onFiltersChange({ strategy_id: e.target.value || undefined })}
            className="w-full bg-argus-surface-2 border border-argus-border rounded-md px-3 py-2 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent min-h-[44px]"
          >
            <option value="">All Strategies</option>
            {strategiesData?.strategies.map((s) => (
              <option key={s.strategy_id} value={s.strategy_id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        {/* Outcome segmented tab */}
        <div className="w-full lg:w-auto lg:flex-shrink-0">
          <label className="block text-xs text-argus-text-dim uppercase tracking-wide mb-1">
            Outcome
          </label>
          <SegmentedTab
            segments={outcomeSegments}
            activeValue={outcome}
            onChange={(value) => onFiltersChange({ outcome: value as OutcomeFilter })}
            size="sm"
            layoutId="trade-outcome-filter"
          />
        </div>

        {/* Date range */}
        <div className="flex gap-3 w-full lg:flex-1">
          <div className="flex-1 min-w-0">
            <label className="block text-xs text-argus-text-dim uppercase tracking-wide mb-1">
              From
            </label>
            <input
              type="date"
              value={date_from || ''}
              onChange={(e) => {
                const newFrom = e.target.value || undefined;
                // Clear "To" if new "From" is after current "To"
                if (newFrom && date_to && newFrom > date_to) {
                  onFiltersChange({ date_from: newFrom, date_to: undefined });
                } else {
                  onFiltersChange({ date_from: newFrom });
                }
              }}
              className="w-full bg-argus-surface-2 border border-argus-border rounded-md px-2 py-2 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent min-h-[44px]"
            />
          </div>
          <div className="flex-1 min-w-0">
            <label className="block text-xs text-argus-text-dim uppercase tracking-wide mb-1">
              To
            </label>
            <input
              type="date"
              value={date_to || ''}
              min={date_from || ''}
              onChange={(e) => {
                const newTo = e.target.value || undefined;
                // Reject if To is before From (iOS Safari ignores min attribute)
                if (newTo && date_from && newTo < date_from) {
                  return;
                }
                onFiltersChange({ date_to: newTo });
              }}
              className="w-full bg-argus-surface-2 border border-argus-border rounded-md px-2 py-2 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent min-h-[44px]"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
