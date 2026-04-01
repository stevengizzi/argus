/**
 * Trade stats bar showing summary statistics for the current filtered set.
 *
 * Displays: total trades, win rate, net P&L, avg R.
 * Uses server-side stats endpoint (resolves DEF-102 / DEF-117).
 * Container is stable; content dims during filter transitions.
 */

import { MetricCard } from '../../components/MetricCard';
import { formatCurrency, formatPercentRaw, formatPnl } from '../../utils/format';
import type { TradeStatsResponse } from '../../api/types';

interface TradeStatsBarProps {
  stats: TradeStatsResponse;
  isTransitioning?: boolean;
}

export function TradeStatsBar({ stats, isTransitioning = false }: TradeStatsBarProps) {
  const { total_trades, wins, losses, win_rate, net_pnl, avg_r } = stats;
  const pnlFormatted = formatPnl(net_pnl);

  return (
    <div className="bg-argus-surface border border-argus-border rounded-lg p-3 md:p-4">
      {/* Fixed-width layout prevents content-driven width shifts when filtering */}
      <div
        className={`flex items-center justify-between gap-4 transition-opacity duration-200 ${
          isTransitioning ? 'opacity-40' : 'opacity-100'
        }`}
      >
        <div className="flex-1 min-w-0">
          <MetricCard
            label="Trades"
            value={total_trades.toString()}
            subValue={`${wins}W / ${losses}L`}
          />
        </div>
        <div className="w-px h-8 bg-argus-border flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <MetricCard
            label="Win Rate"
            value={formatPercentRaw(win_rate * 100)}
            trend={win_rate * 100 >= 50 ? 'up' : win_rate > 0 ? 'down' : 'neutral'}
          />
        </div>
        <div className="w-px h-8 bg-argus-border hidden sm:block flex-shrink-0" />
        <div className="hidden sm:block flex-1 min-w-0">
          <MetricCard
            label="Net P&L"
            value={formatCurrency(net_pnl)}
            trend={net_pnl > 0 ? 'up' : net_pnl < 0 ? 'down' : 'neutral'}
            className={pnlFormatted.className}
          />
        </div>
        <div className="w-px h-8 bg-argus-border hidden sm:block flex-shrink-0" />
        <div className="hidden sm:block flex-1 min-w-0">
          <MetricCard
            label="Avg R"
            value={avg_r != null ? `${avg_r >= 0 ? '+' : ''}${avg_r.toFixed(2)}R` : '—'}
            trend={avg_r != null ? (avg_r > 0 ? 'up' : avg_r < 0 ? 'down' : 'neutral') : 'neutral'}
          />
        </div>
      </div>
    </div>
  );
}
