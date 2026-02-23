/**
 * Responsive grid of key performance metrics.
 *
 * 2 cols mobile, 3 cols tablet, 5-6 cols desktop.
 * Each MetricCard animates in with a stagger effect on mount.
 *
 * Note: MetricsGrid remounts on period change (parent shows skeleton during loading),
 * so the stagger animation naturally plays once per mount — no need for first-mount tracking.
 */

import { motion } from 'framer-motion';
import { MetricCard } from '../../components/MetricCard';
import { Card } from '../../components/Card';
import type { MetricsData } from '../../api/types';
import { formatCurrency, formatPercentRaw, formatDuration } from '../../utils/format';
import { staggerContainer, staggerItem } from '../../utils/motion';

interface MetricsGridProps {
  metrics: MetricsData;
  className?: string;
}

export function MetricsGrid({ metrics, className = '' }: MetricsGridProps) {
  // win_rate from API is a proportion (0.6 = 60%), convert to percentage for display
  const winRatePct = metrics.win_rate * 100;
  const winRateTrend = winRatePct > 50 ? 'up' : winRatePct < 50 ? 'down' : 'neutral';
  const pfTrend = metrics.profit_factor > 1 ? 'up' : metrics.profit_factor < 1 ? 'down' : 'neutral';
  const sharpeTrend = metrics.sharpe_ratio > 0 ? 'up' : metrics.sharpe_ratio < 0 ? 'down' : 'neutral';

  return (
    <Card className={className}>
      <motion.div
        className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4"
        variants={staggerContainer(0.04)}
        initial="hidden"
        animate="show"
      >
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Trades"
            value={metrics.total_trades.toString()}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Win Rate"
            value={formatPercentRaw(winRatePct)}
            trend={winRateTrend}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Profit Factor"
            value={metrics.profit_factor.toFixed(2)}
            trend={pfTrend}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Sharpe"
            value={metrics.sharpe_ratio.toFixed(2)}
            trend={sharpeTrend}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Max DD"
            value={formatPercentRaw(Math.abs(metrics.max_drawdown_pct))}
            subValue="drawdown"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Net P&L"
            value={formatCurrency(metrics.net_pnl)}
            trend={metrics.net_pnl > 0 ? 'up' : metrics.net_pnl < 0 ? 'down' : 'neutral'}
          />
        </motion.div>
      </motion.div>

      {/* Additional metrics row - visible on tablet+ */}
      <motion.div
        className="hidden md:grid grid-cols-4 lg:grid-cols-6 gap-4 mt-4 pt-4 border-t border-argus-border"
        variants={staggerContainer(0.04)}
        initial="hidden"
        animate="show"
      >
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Avg R"
            value={metrics.avg_r_multiple.toFixed(2) + 'R'}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Avg Hold"
            value={formatDuration(metrics.avg_hold_seconds)}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Largest Win"
            value={formatCurrency(metrics.largest_win)}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Largest Loss"
            value={formatCurrency(Math.abs(metrics.largest_loss))}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Win Streak"
            value={metrics.consecutive_wins_max.toString()}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Loss Streak"
            value={metrics.consecutive_losses_max.toString()}
          />
        </motion.div>
      </motion.div>
    </Card>
  );
}
