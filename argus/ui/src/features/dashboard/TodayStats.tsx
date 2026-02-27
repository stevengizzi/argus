/**
 * Today's Stats card showing key daily metrics.
 *
 * Sprint 21d Code Review Fix #4: New component for 3-card row.
 * - 2x2 grid of compact metrics:
 *   - Trades: count
 *   - Win Rate: percentage
 *   - Avg R: R-multiple
 *   - Best Trade: symbol + P&L
 */

import { useMemo } from 'react';
import { Card } from '../../components/Card';
import { usePerformance } from '../../hooks/usePerformance';
import { useTrades } from '../../hooks/useTrades';
import { formatCurrency } from '../../utils/format';

export function TodayStats() {
  const { data: perfData, isLoading: perfLoading } = usePerformance('day');
  const { data: tradesData, isLoading: tradesLoading } = useTrades({ limit: 100 });

  // Find the best trade (highest P&L)
  const bestTrade = useMemo(() => {
    if (!tradesData?.trades.length) return null;

    // Filter to today's trades (if the API doesn't already filter)
    const today = new Date().toISOString().split('T')[0];
    const todaysTrades = tradesData.trades.filter(
      (t) => t.entry_time.startsWith(today)
    );

    if (todaysTrades.length === 0) return null;

    // Find the trade with highest P&L
    return todaysTrades.reduce((best, trade) => {
      const tradePnl = trade.realized_pnl ?? 0;
      const bestPnl = best.realized_pnl ?? 0;
      return tradePnl > bestPnl ? trade : best;
    }, todaysTrades[0]);
  }, [tradesData]);

  // Loading state
  if (perfLoading || tradesLoading) {
    return (
      <Card className="h-full">
        <div className="animate-pulse">
          <div className="h-3 w-20 bg-argus-surface-2 rounded mb-3" />
          <div className="grid grid-cols-2 gap-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i}>
                <div className="h-2 w-12 bg-argus-surface-2 rounded mb-1" />
                <div className="h-4 w-16 bg-argus-surface-2 rounded" />
              </div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  const metrics = perfData?.metrics;
  const trades = metrics?.total_trades ?? 0;
  const winRate = metrics?.win_rate ?? 0;
  const avgR = metrics?.avg_r_multiple ?? 0;

  return (
    <Card className="h-full flex flex-col">
      {/* Header */}
      <h3 className="text-xs font-medium uppercase tracking-wider text-argus-text-dim mb-3">
        Today's Stats
      </h3>

      {/* 2x2 metrics grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 flex-1">
        {/* Trades */}
        <div>
          <div className="text-[10px] uppercase tracking-wide text-argus-text-dim">
            Trades
          </div>
          <div className="text-lg font-semibold text-argus-text tabular-nums">
            {trades}
          </div>
        </div>

        {/* Win Rate */}
        <div>
          <div className="text-[10px] uppercase tracking-wide text-argus-text-dim">
            Win Rate
          </div>
          <div className={`text-lg font-semibold tabular-nums ${
            winRate >= 50 ? 'text-argus-profit' : winRate > 0 ? 'text-argus-loss' : 'text-argus-text'
          }`}>
            {winRate > 0 ? `${winRate.toFixed(0)}%` : '—'}
          </div>
        </div>

        {/* Avg R */}
        <div>
          <div className="text-[10px] uppercase tracking-wide text-argus-text-dim">
            Avg R
          </div>
          <div className={`text-lg font-semibold tabular-nums ${
            avgR > 0 ? 'text-argus-profit' : avgR < 0 ? 'text-argus-loss' : 'text-argus-text'
          }`}>
            {avgR !== 0 ? `${avgR >= 0 ? '+' : ''}${avgR.toFixed(1)}R` : '—'}
          </div>
        </div>

        {/* Best Trade */}
        <div>
          <div className="text-[10px] uppercase tracking-wide text-argus-text-dim">
            Best Trade
          </div>
          {bestTrade ? (
            <div className="text-sm font-medium">
              <span className="text-argus-text">{bestTrade.symbol}</span>
              <span className="text-argus-profit ml-1">
                +{formatCurrency(bestTrade.realized_pnl ?? 0)}
              </span>
            </div>
          ) : (
            <div className="text-lg font-semibold text-argus-text-dim">—</div>
          )}
        </div>
      </div>
    </Card>
  );
}
