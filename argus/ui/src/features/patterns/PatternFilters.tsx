/**
 * Filter and sort controls for the Pattern Library card grid.
 *
 * Note: Stage filter is controlled by IncubatorPipeline clicks, not shown here.
 * This component shows family, time window filters, and sort controls.
 */

import { ChevronDown } from 'lucide-react';

interface PatternFiltersProps {
  filters: {
    stage: string | null;
    family: string | null;
    timeWindow: string | null;
  };
  sortBy: string;
  onFilterChange: (key: 'stage' | 'family' | 'timeWindow', value: string | null) => void;
  onSortChange: (sort: string) => void;
}

const FAMILY_OPTIONS = [
  { value: null, label: 'All Families' },
  { value: 'orb_family', label: 'ORB Family' },
  { value: 'momentum', label: 'Momentum' },
  { value: 'mean_reversion', label: 'Mean-Reversion' },
];

const TIME_OPTIONS = [
  { value: null, label: 'All Times' },
  { value: 'morning', label: 'Morning' },
  { value: 'afternoon', label: 'Afternoon' },
];

const SORT_OPTIONS = [
  { value: 'name', label: 'Name (A→Z)' },
  { value: 'pnl', label: 'P&L (high→low)' },
  { value: 'win_rate', label: 'Win Rate (high→low)' },
  { value: 'trades', label: 'Trades (high→low)' },
];

export function PatternFilters({
  filters,
  sortBy,
  onFilterChange,
  onSortChange,
}: PatternFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      {/* Family filter */}
      <FilterSelect
        value={filters.family}
        options={FAMILY_OPTIONS}
        onChange={(value) => onFilterChange('family', value)}
      />

      {/* Time window filter */}
      <FilterSelect
        value={filters.timeWindow}
        options={TIME_OPTIONS}
        onChange={(value) => onFilterChange('timeWindow', value)}
      />

      {/* Spacer */}
      <div className="flex-1 min-w-4" />

      {/* Sort control */}
      <FilterSelect
        value={sortBy}
        options={SORT_OPTIONS}
        onChange={(value) => value && onSortChange(value)}
        label="Sort:"
      />
    </div>
  );
}

interface FilterSelectProps {
  value: string | null;
  options: { value: string | null; label: string }[];
  onChange: (value: string | null) => void;
  label?: string;
}

function FilterSelect({ value, options, onChange, label }: FilterSelectProps) {
  return (
    <div className="relative">
      {label && (
        <span className="text-xs text-argus-text-dim mr-1.5">{label}</span>
      )}
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
        className="
          appearance-none
          bg-argus-surface-2 border border-argus-border rounded-md
          text-xs text-argus-text
          pl-3 pr-7 py-1.5
          cursor-pointer
          hover:bg-argus-surface-3
          focus:outline-none focus:ring-2 focus:ring-argus-accent
        "
      >
        {options.map((option) => (
          <option key={option.value ?? 'null'} value={option.value ?? ''}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-argus-text-dim pointer-events-none" />
    </div>
  );
}
