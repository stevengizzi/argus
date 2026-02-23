/**
 * Trade stats bar showing summary statistics for the current filtered set.
 *
 * Displays: total trades, win rate, net P&L.
 */

import { MetricCard } from '../../components/MetricCard';
import { formatCurrency, formatPercentRaw, formatPnl } from '../../utils/format';
import type { Trade } from '../../api/types';

interface TradeStatsBarProps {
  trades: Trade[];
  totalCount: number;
}

export function TradeStatsBar({ trades, totalCount }: TradeStatsBarProps) {
  // Calculate stats from the filtered trades
  const wins = trades.filter((t) => (t.pnl_dollars ?? 0) > 0).length;
  const losses = trades.filter((t) => (t.pnl_dollars ?? 0) < 0).length;

  // Win rate calculation (only count completed trades with P&L)
  const tradesWithPnl = trades.filter((t) => t.pnl_dollars !== null);
  const winRate = tradesWithPnl.length > 0 ? (wins / tradesWithPnl.length) * 100 : 0;

  // Net P&L calculation
  const netPnl = trades.reduce((sum, t) => sum + (t.pnl_dollars ?? 0), 0);
  const pnlFormatted = formatPnl(netPnl);

  return (
    <div className="bg-argus-surface border border-argus-border rounded-lg p-3 md:p-4">
      {/* Fixed-width layout prevents content-driven width shifts when filtering */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 min-w-0">
          <MetricCard
            label="Trades"
            value={totalCount.toString()}
            subValue={`${wins}W / ${losses}L`}
          />
        </div>
        <div className="w-px h-8 bg-argus-border flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <MetricCard
            label="Win Rate"
            value={formatPercentRaw(winRate)}
            trend={winRate >= 50 ? 'up' : winRate > 0 ? 'down' : 'neutral'}
          />
        </div>
        <div className="w-px h-8 bg-argus-border hidden sm:block flex-shrink-0" />
        <div className="hidden sm:block flex-1 min-w-0">
          <MetricCard
            label="Net P&L"
            value={netPnl >= 0 ? formatCurrency(netPnl) : formatCurrency(netPnl)}
            trend={netPnl > 0 ? 'up' : netPnl < 0 ? 'down' : 'neutral'}
            className={pnlFormatted.className}
          />
        </div>
      </div>
    </div>
  );
}
