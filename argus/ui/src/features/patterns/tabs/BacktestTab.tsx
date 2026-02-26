/**
 * Backtest tab for Pattern Library detail view.
 *
 * Shows:
 * - Validation status badge
 * - Walk-forward metrics summary
 * - Notes about data validation requirements
 */

import { Card } from '../../../components/Card';
import { Badge } from '../../../components/Badge';
import type { StrategyInfo, BacktestSummary } from '../../../api/types';

interface BacktestTabProps {
  strategy: StrategyInfo;
}

/**
 * Map backtest status to badge variant and display text.
 */
function getStatusBadge(status: string | undefined): {
  variant: 'success' | 'warning' | 'neutral';
  text: string;
} {
  switch (status) {
    case 'walk_forward_complete':
      return { variant: 'success', text: 'Walk-Forward Complete' };
    case 'sweep_complete':
      return { variant: 'warning', text: 'Parameter Sweep Complete' };
    case 'not_validated':
    default:
      return { variant: 'neutral', text: 'Not Yet Validated' };
  }
}

/**
 * Format a metric value with appropriate precision.
 */
function formatMetric(value: number | null | undefined, prefix = '', suffix = ''): string {
  if (value === null || value === undefined) {
    return '—';
  }
  return `${prefix}${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`;
}

/**
 * Format date string for display.
 */
function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

interface MetricItemProps {
  label: string;
  value: string;
}

function MetricItem({ label, value }: MetricItemProps) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-argus-text-dim mb-1">{label}</span>
      <span className="text-sm text-argus-text font-medium tabular-nums">{value}</span>
    </div>
  );
}

export function BacktestTab({ strategy }: BacktestTabProps) {
  const backtest: BacktestSummary | null = strategy.backtest_summary;
  const statusBadge = getStatusBadge(backtest?.status);

  return (
    <div className="space-y-6">
      {/* Status Badge */}
      <Card>
        <div className="flex items-center justify-between">
          <h3 className="text-base font-medium text-argus-text">Validation Status</h3>
          <Badge variant={statusBadge.variant}>{statusBadge.text}</Badge>
        </div>
      </Card>

      {/* Summary Metrics */}
      <Card>
        <h3 className="text-base font-medium text-argus-text mb-4">Backtest Summary</h3>

        {backtest && backtest.status !== 'not_validated' ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            <MetricItem
              label="WFE (P&L)"
              value={formatMetric(backtest.wfe_pnl, '$')}
            />
            <MetricItem
              label="OOS Sharpe"
              value={formatMetric(backtest.oos_sharpe)}
            />
            <MetricItem
              label="Total Trades"
              value={formatMetric(backtest.total_trades)}
            />
            <MetricItem
              label="Data Coverage"
              value={backtest.data_months ? `${backtest.data_months} months` : '—'}
            />
            <MetricItem
              label="Last Run"
              value={formatDate(backtest.last_run)}
            />
          </div>
        ) : (
          <p className="text-sm text-argus-text-dim">
            No backtest data available. Run VectorBT parameter sweep to generate validation metrics.
          </p>
        )}
      </Card>

      {/* Data Validation Note */}
      <Card>
        <div className="flex gap-3">
          <span className="text-argus-warning text-lg">⚠️</span>
          <div>
            <p className="text-sm text-argus-text">
              All pre-Databento backtests require re-validation with exchange-direct data (DEC-132).
            </p>
          </div>
        </div>
      </Card>

      {/* Future Placeholder */}
      <Card>
        <h3 className="text-base font-medium text-argus-text mb-2">Coming Soon</h3>
        <p className="text-sm text-argus-text-dim">
          Interactive backtest explorer, VectorBT sweep heatmaps, and walk-forward visualizations
          coming in Sprint 21d.
        </p>
      </Card>
    </div>
  );
}
