/**
 * Goal tracker card showing monthly target progress.
 *
 * Sprint 21d Session 5 (DEC-204): Dashboard goal tracker.
 * - Shows monthly target, current P&L, percentage progress, days remaining
 * - Thin progress bar with color logic:
 *   - Green: on pace (current_pnl / elapsed_pct >= target)
 *   - Amber: behind but within 80% of pace
 *   - Red: significantly behind (<80% of pace)
 * - Trading days calculation: ~22 days/month, count weekdays elapsed vs remaining
 */

import { useMemo } from 'react';
import { Card } from '../../components/Card';
import { useGoals } from '../../hooks/useGoals';
import { usePerformance } from '../../hooks/usePerformance';
import { formatCurrency } from '../../utils/format';

/** Approximate trading days per month */
const TRADING_DAYS_PER_MONTH = 22;

interface TradingDayProgress {
  elapsed: number;
  remaining: number;
  total: number;
  elapsedPct: number;
}

/**
 * Calculate trading days elapsed and remaining in the current month.
 * Counts weekdays (Mon-Fri) only.
 */
function calculateTradingDays(): TradingDayProgress {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();

  // First and last day of current month
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const today = now.getDate();

  // Count weekdays from start of month to today
  let elapsed = 0;
  for (let day = 1; day <= today; day++) {
    const date = new Date(year, month, day);
    const dayOfWeek = date.getDay();
    if (dayOfWeek !== 0 && dayOfWeek !== 6) {
      elapsed++;
    }
  }

  // Count weekdays from today+1 to end of month
  let remaining = 0;
  const lastDate = lastDay.getDate();
  for (let day = today + 1; day <= lastDate; day++) {
    const date = new Date(year, month, day);
    const dayOfWeek = date.getDay();
    if (dayOfWeek !== 0 && dayOfWeek !== 6) {
      remaining++;
    }
  }

  const total = elapsed + remaining;
  const elapsedPct = total > 0 ? (elapsed / total) * 100 : 0;

  return { elapsed, remaining, total, elapsedPct };
}

/**
 * Determine progress bar color based on pace.
 * Green: on pace, Amber: behind but within 80%, Red: significantly behind
 */
function getProgressColor(
  currentPnl: number,
  target: number,
  elapsedPct: number
): { bar: string; text: string } {
  // If no elapsed time, default to neutral
  if (elapsedPct <= 0) {
    return { bar: 'bg-argus-text-dim', text: 'text-argus-text-dim' };
  }

  // Expected progress at this point in the month
  const expectedPnl = target * (elapsedPct / 100);

  // Pace ratio: currentPnl / expectedPnl
  const paceRatio = expectedPnl > 0 ? currentPnl / expectedPnl : currentPnl > 0 ? 2 : 0;

  if (paceRatio >= 1) {
    // On pace or ahead
    return { bar: 'bg-argus-profit', text: 'text-argus-profit' };
  } else if (paceRatio >= 0.8) {
    // Behind but within 80%
    return { bar: 'bg-amber-500', text: 'text-amber-500' };
  } else {
    // Significantly behind
    return { bar: 'bg-argus-loss', text: 'text-argus-loss' };
  }
}

export function GoalTracker() {
  const { data: goalsData, isLoading: goalsLoading } = useGoals();
  const { data: perfData, isLoading: perfLoading } = usePerformance('month');

  const tradingDays = useMemo(() => calculateTradingDays(), []);

  // Loading state
  if (goalsLoading || perfLoading) {
    return (
      <Card className="h-full">
        <div className="animate-pulse">
          <div className="h-4 bg-argus-surface-2 rounded w-24 mb-2" />
          <div className="h-1.5 bg-argus-surface-2 rounded-full w-full mb-2" />
          <div className="h-3 bg-argus-surface-2 rounded w-32" />
        </div>
      </Card>
    );
  }

  const target = goalsData?.monthly_target_usd ?? 5000;
  const currentPnl = perfData?.metrics.net_pnl ?? 0;
  const progressPct = target > 0 ? Math.min((currentPnl / target) * 100, 100) : 0;

  const colors = getProgressColor(currentPnl, target, tradingDays.elapsedPct);

  return (
    <Card className="h-full flex flex-col justify-center">
      {/* Header row: Target | Current | Days remaining */}
      <div className="flex items-center justify-between text-xs mb-2">
        <span className="text-argus-text-dim">
          Target: <span className="text-argus-text">{formatCurrency(target)}/mo</span>
        </span>
        <span className="text-argus-text-dim">
          {tradingDays.remaining} day{tradingDays.remaining !== 1 ? 's' : ''} left
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-argus-surface-2 rounded-full overflow-hidden mb-2">
        <div
          className={`h-full rounded-full transition-all duration-500 ${colors.bar}`}
          style={{ width: `${Math.max(0, progressPct)}%` }}
        />
      </div>

      {/* Current progress */}
      <div className="flex items-center justify-between text-sm">
        <span className={colors.text}>
          {formatCurrency(currentPnl)}
          <span className="text-argus-text-dim ml-1">
            ({progressPct.toFixed(0)}%)
          </span>
        </span>
        <span className="text-xs text-argus-text-dim">
          {currentPnl >= target * (tradingDays.elapsedPct / 100) ? 'On pace' : 'Behind pace'}
        </span>
      </div>
    </Card>
  );
}
