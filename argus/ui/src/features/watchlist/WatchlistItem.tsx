/**
 * WatchlistItem - Single item in the watchlist sidebar.
 *
 * Redesigned layout (Sprint 19, Session 11):
 * - Row 1: Symbol, price, sparkline (right), gap badge
 * - Row 2: Strategy badges + VWAP state dot (tooltip on hover)
 * - Active position (entered) has 3px left border accent
 * - Clickable: opens Trade Detail panel
 */

import type { WatchlistItem as WatchlistItemType, VwapState } from '../../api/types';
import { StrategyBadge } from '../../components/Badge';
import { formatPrice } from '../../utils/format';

interface WatchlistItemProps {
  item: WatchlistItemType;
  onClick?: (symbol: string) => void;
}

// VWAP state indicator colors
const vwapStateColors: Record<VwapState, { dot: string; label: string }> = {
  watching: { dot: 'bg-gray-400', label: 'Watching' },
  above_vwap: { dot: 'bg-blue-400', label: 'Above VWAP' },
  below_vwap: { dot: 'bg-amber-400', label: 'Below VWAP' },
  entered: { dot: 'bg-argus-profit', label: 'Entered' },
};

export function WatchlistItem({ item, onClick }: WatchlistItemProps) {
  const { symbol, current_price, gap_pct, strategies, vwap_state, sparkline } = item;
  const vwapConfig = vwapStateColors[vwap_state];
  const isPositiveGap = gap_pct > 0;
  const isEntered = vwap_state === 'entered';

  const handleClick = () => {
    onClick?.(symbol);
  };

  return (
    <div
      className={`py-1.5 px-2 border-b border-argus-border/50 hover:bg-argus-surface-2/50 transition-colors cursor-pointer ${
        isEntered ? 'border-l-[3px] border-l-argus-profit' : ''
      }`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && handleClick()}
    >
      {/* Row 1: Symbol, price, sparkline (right), gap badge */}
      <div className="flex items-center gap-2">
        <span className="font-semibold text-argus-text text-sm">{symbol}</span>
        <span className="text-xs text-argus-text-dim">{formatPrice(current_price)}</span>

        {/* Sparkline - reduced visual weight */}
        <div className="flex-1 min-w-0">
          <MiniSparkline
            data={sparkline.map((p) => p.price)}
            width={50}
            height={16}
            className="ml-auto"
          />
        </div>

        {/* Gap badge */}
        <span
          className={`text-xs font-medium px-1.5 py-0.5 rounded shrink-0 ${
            isPositiveGap
              ? 'text-argus-profit bg-argus-profit-dim'
              : 'text-argus-loss bg-argus-loss-dim'
          }`}
        >
          {isPositiveGap ? '+' : ''}{gap_pct.toFixed(1)}%
        </span>
      </div>

      {/* Row 2: Strategy badges + VWAP indicator (dot only, tooltip for label) */}
      <div className="flex items-center justify-between mt-1">
        <div className="flex flex-wrap gap-1">
          {strategies.map((strategyId) => (
            <StrategyBadge key={strategyId} strategyId={strategyId} />
          ))}
        </div>

        {/* VWAP state indicator - dot only with tooltip */}
        {strategies.includes('vwap_reclaim') && (
          <div
            className="flex items-center"
            title={vwapConfig.label}
          >
            <span className={`w-2 h-2 rounded-full ${vwapConfig.dot}`} />
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
 * Reduced visual weight: thinner stroke, slight opacity.
 */
export function MiniSparkline({ data, width = 50, height = 16, className = '' }: MiniSparklineProps) {
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
      style={{ width: '100%', height: height, opacity: 0.7 }}
      preserveAspectRatio="none"
    >
      <polyline
        points={points}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
