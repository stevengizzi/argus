/**
 * WatchlistItem - Single item in the watchlist sidebar.
 *
 * Redesigned layout (Sprint 19, Session 12):
 * - Row 1: Symbol (bold), price (dim), gap badge (right-aligned)
 * - Row 2: Compact strategy pills + VWAP state indicator with short label and distance
 * - Active position (entered) has 3px left border accent
 * - Clickable: opens Trade Detail panel
 */

import type { WatchlistItem as WatchlistItemType, VwapState } from '../../api/types';
import { CompactStrategyBadge } from '../../components/Badge';
import { formatPrice } from '../../utils/format';

interface WatchlistItemProps {
  item: WatchlistItemType;
  onClick?: (symbol: string) => void;
}

// VWAP state indicator config
const vwapStateConfig: Record<VwapState, { dot: string; label: string; show: boolean }> = {
  watching: { dot: 'bg-gray-400', label: 'Watching', show: false }, // Don't show for watching state
  above_vwap: { dot: 'bg-blue-400', label: 'Above', show: true },
  below_vwap: { dot: 'bg-amber-400', label: 'Below', show: true },
  entered: { dot: 'bg-argus-profit', label: 'Entered', show: true },
};

export function WatchlistItem({ item, onClick }: WatchlistItemProps) {
  const { symbol, current_price, gap_pct, strategies, vwap_state, vwap_distance_pct } = item;
  const vwapConfig = vwapStateConfig[vwap_state];
  const isPositiveGap = gap_pct > 0;
  const isEntered = vwap_state === 'entered';
  const isVwapTracked = strategies.includes('vwap_reclaim');
  const showVwapIndicator = isVwapTracked && vwapConfig.show;

  const handleClick = () => {
    onClick?.(symbol);
  };

  // Format VWAP distance display
  const formatVwapDistance = (distance: number | null): { arrow: string; text: string; color: string } | null => {
    if (distance === null || distance === undefined) return null;

    const isAbove = distance > 0;
    const arrow = isAbove ? '↑' : '↓';
    const text = `${(Math.abs(distance) * 100).toFixed(1)}%`;

    // Use same color as the state dot
    let color = 'text-argus-text-dim';
    if (vwap_state === 'above_vwap') color = 'text-blue-400';
    else if (vwap_state === 'below_vwap') color = 'text-amber-400';
    else if (vwap_state === 'entered') color = 'text-argus-profit';

    return { arrow, text, color };
  };

  const vwapDistance = formatVwapDistance(vwap_distance_pct);

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
      {/* Row 1: Symbol, price, gap badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-argus-text text-sm">{symbol}</span>
          <span className="text-xs text-argus-text-dim">{formatPrice(current_price)}</span>
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

      {/* Row 2: Compact strategy badges + VWAP state with distance */}
      <div className="flex items-center justify-between mt-1">
        {/* Strategy badges */}
        <div className="flex gap-0.5">
          {strategies.map((strategyId) => (
            <CompactStrategyBadge key={strategyId} strategyId={strategyId} />
          ))}
        </div>

        {/* VWAP state indicator with label and distance */}
        {showVwapIndicator && (
          <div className="flex items-center gap-1 text-xs">
            <span className={`w-2 h-2 rounded-full ${vwapConfig.dot}`} />
            <span className="text-argus-text-dim">{vwapConfig.label}</span>
            {vwapDistance && (
              <span className={vwapDistance.color}>
                {vwapDistance.arrow}{vwapDistance.text}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Keep MiniSparkline export for potential future use (detail panel, etc.)
interface MiniSparklineProps {
  data: number[];
  width?: number;
  height?: number;
  className?: string;
}

/**
 * Simple SVG sparkline for mini price visualization.
 * Shows a polyline of the price data scaled to fit the viewport.
 * Currently not used in watchlist, but available for detail views.
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
