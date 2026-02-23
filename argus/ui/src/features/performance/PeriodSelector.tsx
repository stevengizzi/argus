/**
 * Period selector tab bar for performance page.
 *
 * Supports both controlled mode (via props) and uncontrolled mode (via URL).
 * Controlled mode prevents data flash during page exit animations.
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
  /** Controlled mode: current period value */
  selectedPeriod?: PerformancePeriod;
  /** Controlled mode: callback when period changes */
  onPeriodChange?: (period: PerformancePeriod) => void;
}

export function PeriodSelector({
  className = '',
  selectedPeriod,
  onPeriodChange,
}: PeriodSelectorProps) {
  const [, setSearchParams] = useSearchParams();

  // Use prop if provided (controlled mode), otherwise fall back to default
  const currentPeriod = selectedPeriod ?? 'month';

  const handlePeriodChange = (period: PerformancePeriod) => {
    // Update parent state if in controlled mode
    if (onPeriodChange) {
      onPeriodChange(period);
    }
    // Always sync to URL for bookmarking (replace to avoid history spam)
    setSearchParams({ period }, { replace: true });
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
