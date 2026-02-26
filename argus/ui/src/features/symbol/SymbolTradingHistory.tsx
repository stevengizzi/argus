/**
 * Symbol trading history component.
 *
 * Shows the user's trading history on a specific symbol, including
 * summary stats and a compact list of recent trades.
 */

import { useTrades } from '../../hooks/useTrades';
import { Badge } from '../../components/Badge';
import {
  formatDate,
  formatPrice,
  formatPnl,
  formatR,
  formatPercent,
} from '../../utils/format';

interface SymbolTradingHistoryProps {
  symbol: string;
}

export function SymbolTradingHistory({ symbol }: SymbolTradingHistoryProps) {
  const { data, isLoading } = useTrades({ symbol, limit: 10 });

  // Calculate summary stats from trades
  const trades = data?.trades ?? [];
  const totalTrades = data?.total_count ?? 0;
  const wins = trades.filter((t) => (t.pnl_dollars ?? 0) > 0).length;
  const winRate = totalTrades > 0 ? wins / totalTrades : 0;
  const avgR =
    trades.length > 0
      ? trades.reduce((sum, t) => sum + (t.pnl_r_multiple ?? 0), 0) / trades.length
      : 0;
  const netPnl = trades.reduce((sum, t) => sum + (t.pnl_dollars ?? 0), 0);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-argus-text-dim uppercase tracking-wider">
          Your Trading History
        </h3>
        <div className="bg-argus-surface-2 rounded-lg p-4 animate-pulse">
          <div className="h-4 bg-argus-border rounded w-1/2 mb-2" />
          <div className="h-4 bg-argus-border rounded w-3/4" />
        </div>
      </div>
    );
  }

  if (trades.length === 0) {
    return (
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-argus-text-dim uppercase tracking-wider">
          Your Trading History
        </h3>
        <div className="bg-argus-surface-2 rounded-lg p-4 text-center">
          <span className="text-sm text-argus-text-dim">No trading history for {symbol}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-argus-text-dim uppercase tracking-wider">
        Your Trading History
      </h3>

      {/* Summary stats row */}
      <div className="grid grid-cols-4 gap-3 text-center">
        <div className="bg-argus-surface-2 rounded-lg px-3 py-2">
          <div className="text-xs text-argus-text-dim">Trades</div>
          <div className="text-lg font-semibold tabular-nums">{totalTrades}</div>
        </div>
        <div className="bg-argus-surface-2 rounded-lg px-3 py-2">
          <div className="text-xs text-argus-text-dim">Win %</div>
          <div className="text-lg font-semibold tabular-nums">{formatPercent(winRate)}</div>
        </div>
        <div className="bg-argus-surface-2 rounded-lg px-3 py-2">
          <div className="text-xs text-argus-text-dim">Avg R</div>
          <div className={`text-lg font-semibold tabular-nums ${formatR(avgR).className}`}>
            {formatR(avgR).text}
          </div>
        </div>
        <div className="bg-argus-surface-2 rounded-lg px-3 py-2">
          <div className="text-xs text-argus-text-dim">Net P&L</div>
          <div className={`text-lg font-semibold tabular-nums ${formatPnl(netPnl).className}`}>
            {formatPnl(netPnl).text}
          </div>
        </div>
      </div>

      {/* Recent trades list */}
      <div className="space-y-2">
        {trades.map((trade) => (
          <div
            key={trade.id}
            className="bg-argus-surface-2 rounded-lg px-3 py-2 flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <span className="text-sm text-argus-text-dim">{formatDate(trade.entry_time)}</span>
              <Badge variant={trade.side === 'long' ? 'success' : 'danger'}>
                {trade.side.toUpperCase()}
              </Badge>
              <span className="text-sm text-argus-text-dim">
                {formatPrice(trade.entry_price)}
                {trade.exit_price != null && ` → ${formatPrice(trade.exit_price)}`}
              </span>
            </div>
            <div className="flex items-center gap-3">
              {trade.pnl_r_multiple != null && (
                <span className={`text-sm tabular-nums ${formatR(trade.pnl_r_multiple).className}`}>
                  {formatR(trade.pnl_r_multiple).text}
                </span>
              )}
              {trade.pnl_dollars != null && (
                <span className={`text-sm font-medium tabular-nums ${formatPnl(trade.pnl_dollars).className}`}>
                  {formatPnl(trade.pnl_dollars).text}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
