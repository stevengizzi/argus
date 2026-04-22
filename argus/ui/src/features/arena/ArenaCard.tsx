/**
 * ArenaCard: real-time position card for The Arena page.
 *
 * Displays a MiniChart with price level overlays, P&L, R-multiple, hold timer,
 * and a stop-to-T1 progress bar. Purely presentational — no data fetching.
 */

import { useRef, useEffect, useState, useMemo } from 'react';
import { MiniChart } from './MiniChart';
import type { MiniChartHandle, CandleData } from './MiniChart';
import type { UTCTimestamp } from 'lightweight-charts';
import { StrategyBadge } from '../../components/Badge';

export interface ArenaCardProps {
  symbol: string;
  strategy_id: string;
  pnl: number;
  r_multiple: number;
  hold_seconds: number;
  entry_price: number;
  stop_price: number;
  target_prices: number[];
  trailing_stop_price?: number;
  candles: CandleData[];
  /** ISO 8601 entry timestamp — used to place the entry marker on MiniChart. */
  entry_time?: string;
  /** Live current price from WS tick — used for progress bar when available. */
  currentPrice?: number;
  /**
   * Called after MiniChart mounts so the WS hook can register the chart handle.
   * Receives symbol + handle so the parent can pass a stable `registerChartRef`
   * reference directly without wrapping it in a per-symbol closure each render.
   */
  onChartMount?: (symbol: string, handle: MiniChartHandle | null) => void;
}

function formatHoldTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function formatPnl(pnl: number): string {
  const abs = Math.abs(pnl).toFixed(2);
  return pnl >= 0 ? `+$${abs}` : `-$${abs}`;
}

/**
 * Compute percentage (0–100) showing where currentPrice sits between stop and T1.
 * Returns 0 when stop >= t1 (degenerate range).
 */
export function computeProgressPct(
  currentPrice: number,
  stopPrice: number,
  t1Price: number,
): number {
  if (t1Price <= stopPrice) return 0;
  const pct = (currentPrice - stopPrice) / (t1Price - stopPrice);
  return Math.min(1, Math.max(0, pct)) * 100;
}

export function ArenaCard({
  symbol,
  strategy_id,
  pnl,
  r_multiple,
  hold_seconds,
  entry_price,
  stop_price,
  target_prices,
  trailing_stop_price,
  entry_time,
  candles,
  currentPrice,
  onChartMount,
}: ArenaCardProps) {
  const chartRef = useRef<MiniChartHandle>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(hold_seconds);

  useEffect(() => {
    setElapsedSeconds(hold_seconds);
    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [hold_seconds]);

  // Notify the WS hook when the MiniChart handle is available.
  // Including `symbol` in deps ensures re-registration if symbol ever changes.
  useEffect(() => {
    if (!onChartMount) return;
    onChartMount(symbol, chartRef.current);
    return () => onChartMount(symbol, null);
  }, [onChartMount, symbol]);

  // Stabilize targetPrices reference so MiniChart's price-line effect only
  // re-runs when the values actually change (S9 carry-forward).
  const stableTargetPrices = useMemo(
    () => target_prices,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [target_prices.join(',')],
  );

  const pnlPositive = pnl >= 0;
  const t1Price = stableTargetPrices[0] ?? 0;
  const latestClose = candles[candles.length - 1]?.close ?? entry_price;
  const priceForProgress = currentPrice ?? latestClose;
  const progressPct = computeProgressPct(priceForProgress, stop_price, t1Price);
  const entryTime = entry_time
    ? (Math.floor(new Date(entry_time).getTime() / 1000) as UTCTimestamp)
    : undefined;

  return (
    // No border — cards use bg-argus-surface-2 background only (S3 cleanup)
    <div
      className="rounded-lg bg-argus-surface-2 flex flex-col overflow-hidden"
      data-testid="arena-card"
    >
      {/* Header row: strategy badge + symbol (left), P&L + R (right) */}
      <div className="flex items-center justify-between px-3 pt-2 pb-1">
        <div className="flex items-center gap-2">
          <StrategyBadge strategyId={strategy_id} data-testid="strategy-badge" />
          <span className="text-sm font-bold text-argus-text" data-testid="symbol-label">
            {symbol}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`text-sm font-bold tabular-nums ${pnlPositive ? 'text-green-400' : 'text-red-400'}`}
            data-testid="pnl-label"
          >
            {formatPnl(pnl)}
          </span>
          <span
            className={`text-xs tabular-nums ${pnlPositive ? 'text-green-400' : 'text-red-400'}`}
            data-testid="r-multiple-label"
          >
            {r_multiple >= 0 ? '+' : ''}
            {r_multiple.toFixed(2)}R
          </span>
        </div>
      </div>

      {/* Chart: fills available vertical space */}
      <div className="flex-1 min-h-0">
        <MiniChart
          ref={chartRef}
          candles={candles}
          entryPrice={entry_price}
          stopPrice={stop_price}
          targetPrices={stableTargetPrices}
          trailingStopPrice={trailing_stop_price}
          entryTime={entryTime}
        />
      </div>

      {/* Footer: progress bar then hold timer */}
      <div className="px-3 pb-2 pt-1">
        {/* Stop/T1 labels + red-to-green gradient track */}
        <div className="flex items-center gap-1 mb-2">
          <span className="text-[10px] text-argus-text-dim" data-testid="progress-label-stop">
            Stop
          </span>
          <div
            className="relative flex-1 h-1 rounded-full overflow-visible"
            style={{ background: 'linear-gradient(to right, #ef4444, #22c55e)' }}
            data-testid="progress-bar-track"
          >
            <div
              className="absolute top-1/2 -translate-y-1/2 w-1.5 h-2.5 rounded-sm bg-white/80"
              style={{ left: `calc(${progressPct}% - 3px)` }}
              data-testid="progress-bar-indicator"
            />
          </div>
          <span className="text-[10px] text-argus-text-dim" data-testid="progress-label-t1">
            T1
          </span>
        </div>
        <span
          className="text-xs text-argus-text-dim tabular-nums"
          data-testid="hold-timer"
        >
          {formatHoldTime(elapsedSeconds)}
        </span>
      </div>
    </div>
  );
}
