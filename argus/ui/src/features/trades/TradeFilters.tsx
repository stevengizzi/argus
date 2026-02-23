/**
 * Trade filters component with controlled state.
 *
 * Provides: strategy dropdown, outcome toggle (wins/losses/breakeven), date range.
 * Parent component controls filter state; URL sync handled by parent.
 */

import { useStrategies } from '../../hooks/useStrategies';
import type { OutcomeFilter, TradeFilterValues } from '../../hooks/useTradeFilters';

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

  const { strategy_id, outcome, date_from, date_to } = filters;

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
            onChange={(e) => onFiltersChange({ strategy_id: e.target.value || undefined })}
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
                onClick={() => onFiltersChange({ outcome: opt.value })}
                className={`flex-1 md:flex-none px-3 min-h-[44px] text-xs font-medium transition-colors ${
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

        {/* Date range */}
        <div className="flex gap-3 w-full md:flex-1">
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
              className="w-full bg-argus-surface-2 border border-argus-border rounded-md px-2 py-2 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
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
              className="w-full bg-argus-surface-2 border border-argus-border rounded-md px-2 py-2 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
