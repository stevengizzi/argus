/**
 * Trade filters component with URL query param persistence.
 *
 * Provides: strategy dropdown, outcome toggle (wins/losses/breakeven), date range.
 * Filters persist in URL for bookmarking/sharing.
 */

import { useSearchParams } from 'react-router-dom';
import { useStrategies } from '../../hooks/useStrategies';

export type OutcomeFilter = 'all' | 'win' | 'loss' | 'breakeven';

export interface TradeFilterValues {
  strategy_id: string | undefined;
  outcome: OutcomeFilter;
  date_from: string | undefined;
  date_to: string | undefined;
}

interface TradeFiltersProps {
  onFiltersChange?: (filters: TradeFilterValues) => void;
}

export function TradeFilters({ onFiltersChange }: TradeFiltersProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: strategiesData } = useStrategies();

  // Read current filter values from URL
  const strategy_id = searchParams.get('strategy') || undefined;
  const outcome = (searchParams.get('outcome') as OutcomeFilter) || 'all';
  const date_from = searchParams.get('from') || undefined;
  const date_to = searchParams.get('to') || undefined;

  // Update URL and notify parent
  const updateFilters = (updates: Partial<TradeFilterValues>) => {
    const newParams = new URLSearchParams(searchParams);

    if (updates.strategy_id !== undefined) {
      if (updates.strategy_id) {
        newParams.set('strategy', updates.strategy_id);
      } else {
        newParams.delete('strategy');
      }
    }

    if (updates.outcome !== undefined) {
      if (updates.outcome === 'all') {
        newParams.delete('outcome');
      } else {
        newParams.set('outcome', updates.outcome);
      }
    }

    if (updates.date_from !== undefined) {
      if (updates.date_from) {
        newParams.set('from', updates.date_from);
      } else {
        newParams.delete('from');
      }
    }

    if (updates.date_to !== undefined) {
      if (updates.date_to) {
        newParams.set('to', updates.date_to);
      } else {
        newParams.delete('to');
      }
    }

    // Reset to page 1 when filters change
    newParams.delete('page');

    setSearchParams(newParams, { replace: true });

    if (onFiltersChange) {
      onFiltersChange({
        strategy_id: newParams.get('strategy') || undefined,
        outcome: (newParams.get('outcome') as OutcomeFilter) || 'all',
        date_from: newParams.get('from') || undefined,
        date_to: newParams.get('to') || undefined,
      });
    }
  };

  const outcomeOptions: { value: OutcomeFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'win', label: 'Wins' },
    { value: 'loss', label: 'Losses' },
    { value: 'breakeven', label: 'BE' },
  ];

  return (
    <div className="bg-argus-surface border border-argus-border rounded-lg p-3 md:p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
        {/* Strategy dropdown */}
        <div className="flex-1 min-w-0">
          <label className="block text-xs text-argus-text-dim uppercase tracking-wide mb-1">
            Strategy
          </label>
          <select
            value={strategy_id || ''}
            onChange={(e) => updateFilters({ strategy_id: e.target.value || undefined })}
            className="w-full bg-argus-surface-2 border border-argus-border rounded-md px-3 py-2 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
          >
            <option value="">All Strategies</option>
            {strategiesData?.strategies.map((s) => (
              <option key={s.strategy_id} value={s.strategy_id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        {/* Outcome toggle */}
        <div className="w-full md:w-auto md:flex-shrink-0">
          <label className="block text-xs text-argus-text-dim uppercase tracking-wide mb-1">
            Outcome
          </label>
          <div className="flex rounded-md border border-argus-border overflow-hidden">
            {outcomeOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => updateFilters({ outcome: opt.value })}
                className={`flex-1 md:flex-none px-3 py-2 text-xs font-medium transition-colors ${
                  outcome === opt.value
                    ? 'bg-argus-accent text-white'
                    : 'bg-argus-surface-2 text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-3'
                } ${opt.value !== outcomeOptions[0].value ? 'border-l border-argus-border' : ''}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Date range - grid ensures 50/50 split on mobile */}
        <div className="grid grid-cols-2 gap-2 md:flex md:gap-2 md:flex-1 md:min-w-0">
          <div className="min-w-0">
            <label className="block text-xs text-argus-text-dim uppercase tracking-wide mb-1">
              From
            </label>
            <input
              type="date"
              value={date_from || ''}
              onChange={(e) => updateFilters({ date_from: e.target.value || undefined })}
              className="w-full bg-argus-surface-2 border border-argus-border rounded-md px-2 py-2 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
            />
          </div>
          <div className="min-w-0">
            <label className="block text-xs text-argus-text-dim uppercase tracking-wide mb-1">
              To
            </label>
            <input
              type="date"
              value={date_to || ''}
              onChange={(e) => updateFilters({ date_to: e.target.value || undefined })}
              className="w-full bg-argus-surface-2 border border-argus-border rounded-md px-2 py-2 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook to read filter values from URL search params.
 */
export function useTradeFilters(): TradeFilterValues {
  const [searchParams] = useSearchParams();

  return {
    strategy_id: searchParams.get('strategy') || undefined,
    outcome: (searchParams.get('outcome') as OutcomeFilter) || 'all',
    date_from: searchParams.get('from') || undefined,
    date_to: searchParams.get('to') || undefined,
  };
}
