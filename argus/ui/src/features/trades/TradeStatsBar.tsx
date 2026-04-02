/**
 * Trade stats bar showing summary statistics for the current filtered set.
 *
 * Displays: total trades, win rate, net P&L, avg R.
 * Uses server-side stats endpoint (resolves DEF-102 / DEF-117).
 * Container is stable; content dims during filter transitions.
 * Sprint 32.8 S6g: grid layout matches Shadow Trades SummaryStats styling.
 */

import { formatCurrency, formatPercentRaw, formatPnl } from '../../utils/format';
import type { TradeStatsResponse } from '../../api/types';

interface TradeStatsBarProps {
  stats: TradeStatsResponse;
  isTransitioning?: boolean;
}

export function TradeStatsBar({ stats, isTransitioning = false }: TradeStatsBarProps) {
  const { total_trades, wins, losses, win_rate, net_pnl, avg_r } = stats;
  const pnlFormatted = formatPnl(net_pnl);

  const statClass = 'flex flex-col gap-0.5';
  const labelClass = 'text-xs text-argus-text-dim uppercase tracking-wide';
  const valueClass = 'text-sm font-semibold text-argus-text';

  return (
    <div
      className={`grid grid-cols-2 sm:grid-cols-4 gap-4 px-4 py-3 rounded-lg border border-argus-border bg-argus-surface-2/50 transition-opacity duration-200 ${
        isTransitioning ? 'opacity-40' : 'opacity-100'
      }`}
    >
      <div className={statClass}>
        <span className={labelClass}>Trades</span>
        <span className={valueClass}>
          {total_trades}{' '}
          <span className="text-xs font-normal text-argus-text-dim">
            {wins}W / {losses}L
          </span>
        </span>
      </div>
      <div className={statClass}>
        <span className={labelClass}>Win Rate</span>
        <span
          className={`text-sm font-semibold tabular-nums leading-none ${
            win_rate * 100 >= 50
              ? 'text-argus-profit'
              : win_rate > 0
              ? 'text-argus-loss'
              : 'text-argus-text'
          }`}
        >
          {formatPercentRaw(win_rate * 100)}
        </span>
      </div>
      <div className={statClass}>
        <span className={labelClass}>Net P&L</span>
        <span className={`text-sm font-semibold tabular-nums leading-none ${pnlFormatted.className}`}>
          {formatCurrency(net_pnl)}
        </span>
      </div>
      <div className={statClass}>
        <span className={labelClass}>Avg R</span>
        <span
          className={`text-sm font-semibold tabular-nums leading-none ${
            avg_r != null
              ? avg_r > 0
                ? 'text-argus-profit'
                : avg_r < 0
                ? 'text-argus-loss'
                : 'text-argus-text'
              : 'text-argus-text'
          }`}
        >
          {avg_r != null ? `${avg_r >= 0 ? '+' : ''}${avg_r.toFixed(2)}R` : '—'}
        </span>
      </div>
    </div>
  );
}
