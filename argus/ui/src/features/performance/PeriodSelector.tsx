/**
 * Period selector tab bar for performance page.
 *
 * Manages URL query param for selected period.
 */

import { useSearchParams } from 'react-router-dom';
import type { PerformancePeriod } from '../../api/types';

const periods: { value: PerformancePeriod; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
  { value: 'all', label: 'All' },
];

interface PeriodSelectorProps {
  className?: string;
}

export function PeriodSelector({ className = '' }: PeriodSelectorProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentPeriod = (searchParams.get('period') as PerformancePeriod) || 'month';

  const handlePeriodChange = (period: PerformancePeriod) => {
    setSearchParams({ period });
  };

  return (
    <div className={`flex gap-1 ${className}`}>
      {periods.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => handlePeriodChange(value)}
          className={`px-3 min-h-[44px] text-sm font-medium rounded transition-colors ${
            currentPeriod === value
              ? 'bg-argus-accent text-white'
              : 'bg-argus-surface-2 text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-3'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
