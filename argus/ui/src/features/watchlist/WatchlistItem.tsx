/**
 * WatchlistItem - Single item in the watchlist sidebar.
 *
 * Shows:
 * - Symbol name + current price
 * - Gap % badge
 * - Mini sparkline (SVG, 50×20px)
 * - Strategy badges (ORB, SCALP, VWAP)
 * - VWAP state indicator (colored dot)
 */

import type { WatchlistItem as WatchlistItemType, VwapState } from '../../api/types';
import { StrategyBadge } from '../../components/Badge';
import { formatPrice } from '../../utils/format';

interface WatchlistItemProps {
  item: WatchlistItemType;
}

// VWAP state indicator colors
const vwapStateColors: Record<VwapState, { dot: string; label: string }> = {
  watching: { dot: 'bg-gray-400', label: 'Watching' },
  above_vwap: { dot: 'bg-blue-400', label: 'Above VWAP' },
  below_vwap: { dot: 'bg-amber-400', label: 'Below VWAP' },
  entered: { dot: 'bg-argus-profit', label: 'Entered' },
};

export function WatchlistItem({ item }: WatchlistItemProps) {
  const { symbol, current_price, gap_pct, strategies, vwap_state, sparkline } = item;
  const vwapConfig = vwapStateColors[vwap_state];
  const isPositiveGap = gap_pct > 0;

  return (
    <div className="p-2 border-b border-argus-border/50 hover:bg-argus-surface-2/50 transition-colors">
      {/* Row 1: Symbol, price, gap badge */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-argus-text">{symbol}</span>
          <span className="text-sm text-argus-text-dim">{formatPrice(current_price)}</span>
        </div>
        <span
          className={`text-xs font-medium px-1.5 py-0.5 rounded ${
            isPositiveGap
              ? 'text-argus-profit bg-argus-profit-dim'
              : 'text-argus-loss bg-argus-loss-dim'
          }`}
        >
          {isPositiveGap ? '+' : ''}{gap_pct.toFixed(1)}%
        </span>
      </div>

      {/* Row 2: Sparkline */}
      <div className="mb-1.5">
        <MiniSparkline
          data={sparkline.map((p) => p.price)}
          width={50}
          height={20}
          className="w-full"
        />
      </div>

      {/* Row 3: Strategy badges + VWAP indicator */}
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-1">
          {strategies.map((strategyId) => (
            <StrategyBadge key={strategyId} strategyId={strategyId} />
          ))}
        </div>

        {/* VWAP state indicator */}
        {strategies.includes('vwap_reclaim') && (
          <div className="flex items-center gap-1" title={vwapConfig.label}>
            <span className={`w-2 h-2 rounded-full ${vwapConfig.dot}`} />
            <span className="text-xs text-argus-text-dim">{vwapConfig.label}</span>
          </div>
        )}
      </div>
    </div>
  );
}

interface MiniSparklineProps {
  data: number[];
  width?: number;
  height?: number;
  className?: string;
}

/**
 * Simple SVG sparkline for mini price visualization.
 * Shows a polyline of the price data scaled to fit the viewport.
 */
function MiniSparkline({ data, width = 50, height = 20, className = '' }: MiniSparklineProps) {
  if (data.length < 2) {
    return <div style={{ width, height }} className={className} />;
  }

  // Find min/max for scaling
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1; // Avoid division by zero

  // Calculate points
  const points = data
    .map((value, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  // Determine color based on trend (first vs last)
  const isUptrend = data[data.length - 1] > data[0];
  const strokeColor = isUptrend ? 'var(--color-argus-profit)' : 'var(--color-argus-loss)';

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      style={{ width: '100%', height: height }}
      preserveAspectRatio="none"
    >
      <polyline
        points={points}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
