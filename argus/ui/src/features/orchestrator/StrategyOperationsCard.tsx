/**
 * Strategy Operations Card — per-strategy status and controls.
 *
 * Displays:
 * - Header: strategy name, badge, status dot, pause/resume button
 * - Allocation: allocated and deployed amounts with progress bar
 * - Throttle section (when throttled): badge, reason, metrics, override button
 * - Performance: trades, P&L, open positions
 * - Operating window: time range and active status
 */

import { Play, Pause, ShieldAlert, ListChecks, OctagonAlert } from 'lucide-react';
import { Card } from '../../components/Card';
import { StrategyBadge, ThrottleBadge } from '../../components/Badge';
import { AnimatedNumber } from '../../components/AnimatedNumber';
import { StatusDot } from '../../components/StatusDot';
import { PnlValue } from '../../components/PnlValue';
import { usePauseStrategy, useResumeStrategy } from '../../hooks/useControls';
import { useOrchestratorUI } from '../../stores/orchestratorUI';
import { formatCurrencyCompact, formatPercent } from '../../utils/format';
import {
  getStrategyDisplay,
  getStrategyBorderClass,
  getStrategyBarClass,
} from '../../utils/strategyConfig';
import type { AllocationInfo } from '../../api/types';

interface StrategyOperationsCardProps {
  allocation: AllocationInfo;
  onViewDecisions?: (strategyId: string) => void;
}

/**
 * Format operating window time from "09:35" to "9:35 AM"
 */
function formatWindowTime(time: string): string {
  const [h, m] = time.split(':').map(Number);
  const hour12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  const ampm = h >= 12 ? 'PM' : 'AM';
  return `${hour12}:${m.toString().padStart(2, '0')} ${ampm}`;
}

/**
 * Check if current ET time is within the operating window
 */
function isWithinWindow(earliest: string, latest: string): boolean {
  const now = new Date();
  const etTime = now.toLocaleString('en-US', { timeZone: 'America/New_York' });
  const etDate = new Date(etTime);
  const currentMinutes = etDate.getHours() * 60 + etDate.getMinutes();

  const [earliestH, earliestM] = earliest.split(':').map(Number);
  const [latestH, latestM] = latest.split(':').map(Number);

  const earliestMinutes = earliestH * 60 + earliestM;
  const latestMinutes = latestH * 60 + latestM;

  return currentMinutes >= earliestMinutes && currentMinutes <= latestMinutes;
}

/**
 * Derive health status from allocation state
 */
function deriveHealthStatus(alloc: AllocationInfo): 'healthy' | 'degraded' | 'error' {
  if (alloc.health_status === 'error') return 'error';
  if (alloc.health_status === 'warning' || alloc.health_status === 'degraded') return 'degraded';
  if (!alloc.is_active) return 'degraded';
  if (alloc.is_throttled) return 'degraded';
  return 'healthy';
}

export function StrategyOperationsCard({ allocation, onViewDecisions }: StrategyOperationsCardProps) {
  const pauseMutation = usePauseStrategy();
  const resumeMutation = useResumeStrategy();
  const openOverrideDialog = useOrchestratorUI((s) => s.openOverrideDialog);

  const strategyConfig = getStrategyDisplay(allocation.strategy_id);
  const strategyName = strategyConfig.name;
  const borderClass = getStrategyBorderClass(allocation.strategy_id);
  const barColorClass = getStrategyBarClass(allocation.strategy_id);
  const healthStatus = deriveHealthStatus(allocation);
  const isThrottled = allocation.throttle_action !== 'none' && allocation.throttle_action !== 'NONE';

  // Deployment percentage relative to allocation
  const deployedOfAllocated =
    allocation.allocation_dollars > 0
      ? (allocation.deployed_capital / allocation.allocation_dollars) * 100
      : 0;

  // Operating window
  const hasWindow = allocation.operating_window !== null;
  const windowActive =
    hasWindow &&
    isWithinWindow(
      allocation.operating_window!.earliest_entry,
      allocation.operating_window!.latest_entry
    );

  const handlePauseResume = () => {
    if (allocation.is_active) {
      pauseMutation.mutate(allocation.strategy_id);
    } else {
      resumeMutation.mutate(allocation.strategy_id);
    }
  };

  const isPending = pauseMutation.isPending || resumeMutation.isPending;

  return (
    <Card className={`border-l-4 ${borderClass}`} fullHeight>
      <div className="space-y-3 flex-1 flex flex-col">
        {/* Header row */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-medium text-argus-text truncate">{strategyName}</span>
            <StrategyBadge strategyId={allocation.strategy_id} />
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <StatusDot status={healthStatus} pulse={allocation.is_active} size="md" />
            {onViewDecisions && (
              <button
                onClick={() => onViewDecisions(allocation.strategy_id)}
                className="p-1.5 rounded-md text-argus-text-dim hover:bg-argus-surface-2
                           hover:text-argus-text transition-colors"
                title="View strategy decisions"
                data-testid="view-decisions-button"
              >
                <ListChecks className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={handlePauseResume}
              disabled={isPending}
              className={`p-1.5 rounded-md transition-colors ${
                allocation.is_active
                  ? 'text-argus-warning hover:bg-argus-warning/10'
                  : 'text-argus-profit hover:bg-argus-profit/10'
              } disabled:opacity-50`}
              title={allocation.is_active ? 'Pause strategy' : 'Resume strategy'}
            >
              {allocation.is_active ? (
                <Pause className="w-4 h-4" />
              ) : (
                <Play className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Allocation section */}
        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between text-sm">
            <span className="text-argus-text-dim">Allocated:</span>
            <span className="font-medium text-argus-text">
              <AnimatedNumber
                value={allocation.allocation_dollars}
                format={formatCurrencyCompact}
              />{' '}
              <span className="text-argus-text-dim">
                ({formatPercent(allocation.allocation_pct)})
              </span>
            </span>
          </div>
          <div className="flex items-baseline justify-between text-xs text-argus-text-dim">
            <span>Deployed:</span>
            <span>
              {formatCurrencyCompact(allocation.deployed_capital)} ({deployedOfAllocated.toFixed(0)}
              %)
            </span>
          </div>
          {/* Progress bar */}
          <div className="h-1.5 bg-argus-surface-2 rounded-full overflow-hidden">
            <div
              className={`h-full ${barColorClass} transition-all duration-300`}
              style={{ width: `${Math.min(deployedOfAllocated, 100)}%` }}
            />
          </div>
        </div>

        {/* Throttle section (only when throttled) */}
        {isThrottled && (
          <div className="p-2 rounded-md bg-amber-400/5 border border-amber-400/20 space-y-2">
            <div className="flex items-center gap-2">
              <ThrottleBadge throttleStatus={allocation.throttle_action.toLowerCase()} />
              <span className="text-xs text-argus-text-dim truncate">{allocation.reason}</span>
            </div>
            {/* Throttle metrics */}
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
              <MetricChip
                label="Losses"
                value={allocation.consecutive_losses}
                warn={allocation.consecutive_losses >= 3}
              />
              <MetricChip
                label="Sharpe"
                value={
                  allocation.rolling_sharpe !== null
                    ? (allocation.rolling_sharpe >= 0 ? '+' : '') +
                      allocation.rolling_sharpe.toFixed(2)
                    : '—'
                }
                warn={allocation.rolling_sharpe !== null && allocation.rolling_sharpe < 0}
              />
              <MetricChip
                label="DD"
                value={`${allocation.drawdown_pct.toFixed(1)}%`}
                warn={allocation.drawdown_pct > 10}
              />
            </div>
            {/* Override button */}
            <button
              onClick={() => openOverrideDialog(allocation.strategy_id)}
              className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded-md
                         bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors"
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              Override Throttle
            </button>
          </div>
        )}

        {/* Suspension section (circuit breaker — not throttled but inactive) */}
        {!allocation.is_active && !isThrottled && (
          <div
            className="p-2 rounded-md bg-red-400/5 border border-red-400/20 space-y-1.5"
            data-testid="suspension-section"
          >
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded bg-red-400/15 text-red-400">
                <OctagonAlert className="w-3 h-3" />
                Suspended
              </span>
            </div>
            <p className="text-xs text-argus-text-dim" data-testid="suspension-reason">
              {allocation.reason || 'Circuit breaker — consecutive losses'}
            </p>
          </div>
        )}

        {/* Performance today */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
          <div className="flex items-center gap-1">
            <span className="text-argus-text-dim">Trades:</span>
            <span className="font-medium text-argus-text">{allocation.trade_count_today}</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-argus-text-dim">P&L:</span>
            <PnlValue value={allocation.daily_pnl} size="sm" />
          </div>
          <div className="flex items-center gap-1">
            <span className="text-argus-text-dim">Open:</span>
            <span className="font-medium text-argus-text">{allocation.open_position_count}</span>
          </div>
        </div>

        {/* Operating window */}
        {hasWindow && (
          <div className="flex items-center justify-between text-xs border-t border-argus-border pt-2 mt-auto">
            <span className="text-argus-text-dim">
              {formatWindowTime(allocation.operating_window!.earliest_entry)} –{' '}
              {formatWindowTime(allocation.operating_window!.latest_entry)} ET
            </span>
            <span
              className={`flex items-center gap-1 ${
                !allocation.is_active
                  ? 'text-red-400'
                  : windowActive
                    ? 'text-argus-profit'
                    : 'text-argus-text-dim'
              }`}
              data-testid="window-status"
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  !allocation.is_active
                    ? 'bg-red-400'
                    : windowActive
                      ? 'bg-argus-profit'
                      : 'bg-argus-text-dim'
                }`}
              />
              {!allocation.is_active ? 'Suspended' : windowActive ? 'Active' : 'Inactive'}
            </span>
          </div>
        )}
      </div>
    </Card>
  );
}

interface MetricChipProps {
  label: string;
  value: string | number;
  warn?: boolean;
}

function MetricChip({ label, value, warn = false }: MetricChipProps) {
  return (
    <span className={`${warn ? 'text-argus-loss' : 'text-argus-text-dim'}`}>
      {label}: <span className="font-medium tabular-nums">{value}</span>
    </span>
  );
}
