/**
 * Position detail slide-in panel for open positions.
 *
 * Shows live position data including entry/current price, P&L, risk levels,
 * and a progress bar visualizing position between stop and target.
 */

import { TrendingUp, Target, Shield, Clock, ExternalLink } from 'lucide-react';
import { SlideInPanel } from '../../components/SlideInPanel';
import { Badge, StrategyBadge } from '../../components/Badge';
import { PnlValue } from '../../components/PnlValue';
import { useSymbolDetailUI } from '../../stores/symbolDetailUI';
import type { Position } from '../../api/types';
import {
  formatPrice,
  formatDuration,
  formatDateTime,
} from '../../utils/format';

interface EnrichedPosition extends Position {
  livePrice: number;
  livePnl: number;
  liveR: number;
}

interface PositionDetailPanelProps {
  position: EnrichedPosition | null;
  onClose: () => void;
}

/**
 * Calculate progress percentage between stop and target.
 * Returns 0-100 where:
 * - 0% = at stop price
 * - 50% = at entry price
 * - 100% = at T1 target
 */
function calculateProgress(
  entryPrice: number,
  currentPrice: number,
  stopPrice: number,
  targetPrice: number,
  side: string
): number {
  const isLong = side === 'long';

  // Calculate total range from stop to target
  const totalRange = isLong
    ? targetPrice - stopPrice
    : stopPrice - targetPrice;

  if (totalRange === 0) return 50;

  // Calculate current position in range
  const currentFromStop = isLong
    ? currentPrice - stopPrice
    : stopPrice - currentPrice;

  const progress = (currentFromStop / totalRange) * 100;

  // Clamp to 0-100 with some overflow allowed for visualization
  return Math.max(0, Math.min(120, progress));
}

/**
 * Get progress bar color based on position.
 */
function getProgressColor(progress: number): string {
  if (progress < 40) return 'bg-argus-loss'; // Near stop
  if (progress < 60) return 'bg-amber-400'; // Near entry
  return 'bg-argus-profit'; // Toward target
}

export function PositionDetailPanel({ position, onClose }: PositionDetailPanelProps) {
  const isOpen = position !== null;
  const { open: openSymbolDetail } = useSymbolDetailUI();

  const handleSymbolClick = () => {
    if (position) {
      openSymbolDetail(position.symbol);
      onClose();
    }
  };

  // Calculate P&L percentage
  const pnlPercent = position
    ? (position.livePnl / (position.entry_price * position.shares_remaining)) * 100
    : null;

  // Calculate progress bar
  const progress = position
    ? calculateProgress(
        position.entry_price,
        position.livePrice,
        position.stop_price,
        position.t1_price,
        position.side
      )
    : 50;

  return (
    <SlideInPanel
      isOpen={isOpen}
      onClose={onClose}
      title={position ? `${position.symbol} — ${position.side.toUpperCase()}` : ''}
      subtitle={position?.entry_time ? formatDateTime(position.entry_time) : undefined}
    >
      {position && (
        <div className="space-y-6">
          {/* Clickable symbol link */}
          <button
            onClick={handleSymbolClick}
            className="flex items-center gap-1.5 text-lg font-semibold text-argus-accent hover:underline transition-colors"
          >
            {position.symbol}
            <ExternalLink className="w-4 h-4" />
          </button>

          {/* Strategy badge + Status */}
          <div className="flex items-center gap-2">
            <StrategyBadge strategyId={position.strategy_id} />
            <Badge variant="success">OPEN</Badge>
          </div>

          {/* P&L Summary */}
          <div className="bg-argus-surface-2 rounded-lg p-4">
            <div className="text-sm text-argus-text-dim mb-1">Unrealized P&L</div>
            <div className="flex items-baseline gap-3">
              <PnlValue value={position.livePnl} size="lg" flash />
              {pnlPercent !== null && (
                <span className={`text-lg tabular-nums ${pnlPercent >= 0 ? 'text-argus-profit' : 'text-argus-loss'}`}>
                  {pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
                </span>
              )}
            </div>
            <div className="mt-1">
              <PnlValue value={position.liveR} format="r-multiple" size="sm" flash />
              <span className="text-sm text-argus-text-dim ml-1">R-multiple</span>
            </div>
          </div>

          {/* Entry / Current */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-argus-surface-2 rounded-lg p-4">
              <div className="flex items-center gap-2 text-argus-text-dim mb-2">
                <TrendingUp className="w-4 h-4" />
                <span className="text-sm">Entry</span>
              </div>
              <div className="text-lg font-medium tabular-nums">{formatPrice(position.entry_price)}</div>
            </div>
            <div className="bg-argus-surface-2 rounded-lg p-4">
              <div className="flex items-center gap-2 text-argus-text-dim mb-2">
                <TrendingUp className="w-4 h-4" />
                <span className="text-sm">Current</span>
              </div>
              <div className="text-lg font-medium tabular-nums">{formatPrice(position.livePrice)}</div>
            </div>
          </div>

          {/* Position Details */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-argus-text-dim uppercase tracking-wider">Details</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-argus-text-dim">Side</span>
                <span className={position.side === 'long' ? 'text-argus-profit' : 'text-argus-loss'}>
                  {position.side.toUpperCase()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-argus-text-dim">Shares</span>
                <span className="tabular-nums">{position.shares_remaining} / {position.shares_total}</span>
              </div>
              <div className="flex justify-between col-span-2">
                <span className="text-argus-text-dim flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Hold Duration
                </span>
                <span className="tabular-nums">{formatDuration(position.hold_duration_seconds)}</span>
              </div>
              {position.t1_filled && (
                <div className="flex justify-between col-span-2">
                  <span className="text-argus-text-dim">T1 Status</span>
                  <Badge variant="success">FILLED</Badge>
                </div>
              )}
            </div>
          </div>

          {/* Price Levels */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-argus-text-dim uppercase tracking-wider">Price Levels</h3>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="flex flex-col items-center p-3 bg-argus-surface-2 rounded-lg">
                <span className="text-argus-text-dim flex items-center gap-1 mb-1">
                  <Shield className="w-3 h-3 text-argus-loss" />
                  Stop
                </span>
                <span className="tabular-nums text-argus-loss font-medium">
                  {formatPrice(position.stop_price)}
                </span>
              </div>
              <div className="flex flex-col items-center p-3 bg-argus-surface-2 rounded-lg">
                <span className="text-argus-text-dim flex items-center gap-1 mb-1">
                  <Target className="w-3 h-3 text-argus-profit" />
                  T1
                </span>
                <span className="tabular-nums text-argus-profit font-medium">
                  {formatPrice(position.t1_price)}
                </span>
              </div>
              <div className="flex flex-col items-center p-3 bg-argus-surface-2 rounded-lg">
                <span className="text-argus-text-dim flex items-center gap-1 mb-1">
                  <Target className="w-3 h-3 text-argus-profit" />
                  T2
                </span>
                <span className="tabular-nums text-argus-profit font-medium">
                  {position.t2_price > 0 ? formatPrice(position.t2_price) : '—'}
                </span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-argus-text-dim">
                <span>Stop</span>
                <span>Entry</span>
                <span>T1</span>
              </div>
              <div className="relative h-2 bg-argus-surface-2 rounded-full overflow-hidden">
                {/* Progress fill */}
                <div
                  className={`absolute top-0 left-0 h-full transition-all duration-300 ${getProgressColor(progress)}`}
                  style={{ width: `${Math.min(progress, 100)}%` }}
                />
                {/* Entry marker (50% position) */}
                <div className="absolute top-0 left-1/2 w-0.5 h-full bg-argus-border -translate-x-1/2" />
              </div>
            </div>
          </div>
        </div>
      )}
    </SlideInPanel>
  );
}
