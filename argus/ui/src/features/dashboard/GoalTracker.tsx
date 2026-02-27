/**
 * Goal tracker card showing monthly target progress.
 *
 * Sprint 21d Code Review Fix #3: Enhanced GoalTracker.
 * - "MONTHLY GOAL" header label
 * - 2-column layout:
 *   - Left (~60%): progress bar, dollar amount, pace status
 *   - Right (~40%): avg daily P&L, need/day to hit target
 * - Target at top with "X days left" right-aligned
 * - Pace calculation: Ahead (>110%), On pace (90-110%), Behind (<90%)
 * - Color-coded status text (green/amber/red)
 */

import { useMemo } from 'react';
import { Card } from '../../components/Card';
import { useGoals } from '../../hooks/useGoals';
import { usePerformance } from '../../hooks/usePerformance';
import { formatCurrency } from '../../utils/format';

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

interface PaceStatus {
  label: string;
  barColor: string;
  textColor: string;
}

/**
 * Determine pace status and colors.
 * Ahead: >110% of pace (green)
 * On pace: 90-110% of pace (green)
 * Behind: <90% of pace (amber if >50%, red if <=50%)
 */
function getPaceStatus(
  currentPnl: number,
  target: number,
  elapsedPct: number
): PaceStatus {
  // If no elapsed time, default to neutral
  if (elapsedPct <= 0) {
    return {
      label: 'Starting',
      barColor: 'bg-argus-text-dim',
      textColor: 'text-argus-text-dim',
    };
  }

  // Expected progress at this point in the month
  const expectedPnl = target * (elapsedPct / 100);

  // Pace ratio: currentPnl / expectedPnl
  const paceRatio = expectedPnl > 0 ? currentPnl / expectedPnl : currentPnl > 0 ? 2 : 0;

  if (paceRatio >= 1.1) {
    return {
      label: 'Ahead of pace',
      barColor: 'bg-argus-profit',
      textColor: 'text-argus-profit',
    };
  } else if (paceRatio >= 0.9) {
    return {
      label: 'On pace',
      barColor: 'bg-argus-profit',
      textColor: 'text-argus-profit',
    };
  } else if (paceRatio >= 0.5) {
    return {
      label: 'Behind pace',
      barColor: 'bg-amber-500',
      textColor: 'text-amber-500',
    };
  } else {
    return {
      label: 'Behind pace',
      barColor: 'bg-argus-loss',
      textColor: 'text-argus-loss',
    };
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
          <div className="h-3 bg-argus-surface-2 rounded w-20 mb-3" />
          <div className="h-4 bg-argus-surface-2 rounded w-32 mb-3" />
          <div className="h-2 bg-argus-surface-2 rounded-full w-full mb-3" />
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="h-3 bg-argus-surface-2 rounded w-24 mb-1" />
              <div className="h-3 bg-argus-surface-2 rounded w-16" />
            </div>
            <div className="flex-1">
              <div className="h-3 bg-argus-surface-2 rounded w-20 mb-1" />
              <div className="h-3 bg-argus-surface-2 rounded w-20" />
            </div>
          </div>
        </div>
      </Card>
    );
  }

  const target = goalsData?.monthly_target_usd ?? 5000;
  const currentPnl = perfData?.metrics.net_pnl ?? 0;
  const progressPct = target > 0 ? Math.min((currentPnl / target) * 100, 100) : 0;

  const paceStatus = getPaceStatus(currentPnl, target, tradingDays.elapsedPct);

  // Calculate avg daily P&L and need/day
  const avgDaily = tradingDays.elapsed > 0 ? currentPnl / tradingDays.elapsed : 0;
  const remainingToTarget = Math.max(0, target - currentPnl);
  const needPerDay = tradingDays.remaining > 0 ? remainingToTarget / tradingDays.remaining : 0;

  return (
    <Card className="h-full flex flex-col">
      {/* Header label */}
      <h3 className="text-xs font-medium uppercase tracking-wider text-argus-text-dim mb-2">
        Monthly Goal
      </h3>

      {/* Target row with days remaining */}
      <div className="flex items-center justify-between text-sm mb-2">
        <span className="text-argus-text font-medium">
          Target: {formatCurrency(target)}/mo
        </span>
        <span className="text-xs text-argus-text-dim">
          {tradingDays.remaining} day{tradingDays.remaining !== 1 ? 's' : ''} left
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-argus-surface-2 rounded-full overflow-hidden mb-3">
        <div
          className={`h-full rounded-full transition-all duration-500 ${paceStatus.barColor}`}
          style={{ width: `${Math.max(0, progressPct)}%` }}
        />
      </div>

      {/* 2-column layout: left (amount + status), right (stats) */}
      <div className="flex gap-4">
        {/* Left column: current amount and status */}
        <div className="flex-1 min-w-0">
          <div className={`text-lg font-semibold tabular-nums ${paceStatus.textColor}`}>
            {formatCurrency(currentPnl)}
            <span className="text-argus-text-dim text-sm font-normal ml-1">
              ({progressPct.toFixed(0)}%)
            </span>
          </div>
          <div className={`text-xs ${paceStatus.textColor}`}>
            {paceStatus.label}
          </div>
        </div>

        {/* Right column: avg daily and need/day */}
        <div className="flex flex-col justify-center text-right text-xs space-y-1">
          <div>
            <span className="text-argus-text-dim">Avg daily: </span>
            <span className={avgDaily >= 0 ? 'text-argus-text' : 'text-argus-loss'}>
              {formatCurrency(avgDaily)}
            </span>
          </div>
          <div>
            <span className="text-argus-text-dim">Need/day: </span>
            <span className="text-argus-text">
              {currentPnl >= target ? formatCurrency(0) : formatCurrency(needPerDay)}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}
