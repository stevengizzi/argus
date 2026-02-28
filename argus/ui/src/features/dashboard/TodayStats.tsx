/**
 * Today's Stats card showing key daily metrics.
 *
 * Sprint 21d Code Review Fix #4: New component for 3-card row.
 * - 2x2 grid of compact metrics:
 *   - Trades: count
 *   - Win Rate: percentage
 *   - Avg R: R-multiple
 *   - Best Trade: symbol + P&L
 *
 * Sprint 21d Dashboard Summary: Accepts optional props from dashboard summary.
 * When props provided, uses them directly (no loading state).
 * When no props, falls back to individual hooks for standalone use.
 */

import { useMemo } from 'react';
import { Card } from '../../components/Card';
import { usePerformance } from '../../hooks/usePerformance';
import { useTrades } from '../../hooks/useTrades';
import { formatCurrency } from '../../utils/format';
import type { TodayStatsData } from '../../api/types';

export interface TodayStatsProps {
  /** Pre-fetched data from dashboard summary. If provided, hooks are skipped. */
  data?: TodayStatsData;
  /** When true, internal hooks are disabled — component waits for props instead of fetching. */
  useSummaryData?: boolean;
}

export function TodayStats({ data: propData, useSummaryData }: TodayStatsProps) {
  // Disable hooks when using summary data mode — component renders structure immediately
  const { data: perfData, isLoading: perfLoading } = usePerformance('today', { enabled: !useSummaryData });
  const { data: tradesData, isLoading: tradesLoading } = useTrades({ limit: 100 }, { enabled: !useSummaryData });

  // In summary mode, never show skeleton — render structure with dash placeholders
  // In standalone mode, show skeleton while hooks are loading
  const isLoading = !useSummaryData && !propData && (perfLoading || tradesLoading);

  // Find the best trade (highest P&L) - only needed when using hooks
  const bestTradeFromHooks = useMemo(() => {
    if (propData || !tradesData?.trades.length) return null;

    // Filter to today's trades (if the API doesn't already filter)
    const today = new Date().toISOString().split('T')[0];
    const todaysTrades = tradesData.trades.filter(
      (t) => t.entry_time.startsWith(today)
    );

    if (todaysTrades.length === 0) return null;

    // Find the trade with highest P&L
    return todaysTrades.reduce((best, trade) => {
      const tradePnl = trade.pnl_dollars ?? 0;
      const bestPnl = best.pnl_dollars ?? 0;
      return tradePnl > bestPnl ? trade : best;
    }, todaysTrades[0]);
  }, [propData, tradesData]);

  // Loading state (only when using hooks)
  if (isLoading) {
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

  // Use props if provided, otherwise fall back to hook data
  let trades: number;
  let winRate: number;
  let avgR: number;
  let bestTrade: { symbol: string; pnl: number } | null;

  if (propData) {
    trades = propData.trade_count;
    winRate = propData.win_rate ?? 0;
    avgR = propData.avg_r ?? 0;
    bestTrade = propData.best_trade;
  } else {
    const metrics = perfData?.metrics;
    trades = metrics?.total_trades ?? 0;
    winRate = metrics?.win_rate ?? 0;
    avgR = metrics?.avg_r_multiple ?? 0;
    bestTrade = bestTradeFromHooks
      ? { symbol: bestTradeFromHooks.symbol, pnl: bestTradeFromHooks.pnl_dollars ?? 0 }
      : null;
  }

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
                +{formatCurrency(bestTrade.pnl)}
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
