/**
 * Responsive grid of key performance metrics.
 *
 * 2 cols mobile, 3 cols tablet, 5-6 cols desktop.
 */

import { MetricCard } from '../../components/MetricCard';
import { Card } from '../../components/Card';
import type { MetricsData } from '../../api/types';
import { formatCurrency, formatPercentRaw, formatDuration } from '../../utils/format';

interface MetricsGridProps {
  metrics: MetricsData;
  className?: string;
}

export function MetricsGrid({ metrics, className = '' }: MetricsGridProps) {
  const winRateTrend = metrics.win_rate > 50 ? 'up' : metrics.win_rate < 50 ? 'down' : 'neutral';
  const pfTrend = metrics.profit_factor > 1 ? 'up' : metrics.profit_factor < 1 ? 'down' : 'neutral';
  const sharpeTrend = metrics.sharpe_ratio > 0 ? 'up' : metrics.sharpe_ratio < 0 ? 'down' : 'neutral';

  return (
    <Card className={className}>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <MetricCard
          label="Trades"
          value={metrics.total_trades.toString()}
        />
        <MetricCard
          label="Win Rate"
          value={formatPercentRaw(metrics.win_rate)}
          trend={winRateTrend}
        />
        <MetricCard
          label="Profit Factor"
          value={metrics.profit_factor.toFixed(2)}
          trend={pfTrend}
        />
        <MetricCard
          label="Sharpe"
          value={metrics.sharpe_ratio.toFixed(2)}
          trend={sharpeTrend}
        />
        <MetricCard
          label="Max DD"
          value={formatPercentRaw(Math.abs(metrics.max_drawdown_pct))}
          subValue="drawdown"
        />
        <MetricCard
          label="Net P&L"
          value={formatCurrency(metrics.net_pnl)}
          trend={metrics.net_pnl > 0 ? 'up' : metrics.net_pnl < 0 ? 'down' : 'neutral'}
        />
      </div>

      {/* Additional metrics row - visible on tablet+ */}
      <div className="hidden md:grid grid-cols-4 lg:grid-cols-6 gap-4 mt-4 pt-4 border-t border-argus-border">
        <MetricCard
          label="Avg R"
          value={metrics.avg_r_multiple.toFixed(2) + 'R'}
        />
        <MetricCard
          label="Avg Hold"
          value={formatDuration(metrics.avg_hold_seconds)}
        />
        <MetricCard
          label="Largest Win"
          value={formatCurrency(metrics.largest_win)}
        />
        <MetricCard
          label="Largest Loss"
          value={formatCurrency(Math.abs(metrics.largest_loss))}
        />
        <MetricCard
          label="Win Streak"
          value={metrics.consecutive_wins_max.toString()}
        />
        <MetricCard
          label="Loss Streak"
          value={metrics.consecutive_losses_max.toString()}
        />
      </div>
    </Card>
  );
}
