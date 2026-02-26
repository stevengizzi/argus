/**
 * Symbol open position detail component.
 *
 * Shows current open position details for a specific symbol (if any).
 * Returns null if no open position exists.
 */

import { Shield, Target, Clock } from 'lucide-react';
import { Badge } from '../../components/Badge';
import { usePositions } from '../../hooks/usePositions';
import {
  formatPrice,
  formatPnl,
  formatPnlPercent,
  formatR,
  formatDuration,
} from '../../utils/format';

interface SymbolPositionDetailProps {
  symbol: string;
}

export function SymbolPositionDetail({ symbol }: SymbolPositionDetailProps) {
  const { data: positionsData } = usePositions();

  // Find the open position for this symbol
  const position = positionsData?.positions.find((p) => p.symbol === symbol);

  // Don't render anything if no position
  if (!position) {
    return null;
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-argus-text-dim uppercase tracking-wider">
        Open Position
      </h3>

      <div className="bg-argus-surface-2 rounded-lg p-4 space-y-4">
        {/* Header row: strategy + side */}
        <div className="flex items-center justify-between">
          <Badge variant="info">{position.strategy_id}</Badge>
          <Badge variant={position.side === 'long' ? 'success' : 'danger'}>
            {position.side.toUpperCase()}
          </Badge>
        </div>

        {/* P&L */}
        <div className="flex items-baseline gap-3">
          <span className={`text-2xl font-bold tabular-nums ${formatPnl(position.unrealized_pnl).className}`}>
            {formatPnl(position.unrealized_pnl).text}
          </span>
          <span className={`text-lg tabular-nums ${formatPnlPercent(position.unrealized_pnl_pct * 100).className}`}>
            {formatPnlPercent(position.unrealized_pnl_pct * 100).text}
          </span>
        </div>

        {/* R-multiple */}
        <div className={`text-sm ${formatR(position.r_multiple_current).className}`}>
          {formatR(position.r_multiple_current).text} R-multiple
        </div>

        {/* Details grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm pt-2 border-t border-argus-border">
          <div className="flex justify-between">
            <span className="text-argus-text-dim">Entry</span>
            <span className="tabular-nums">{formatPrice(position.entry_price)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-argus-text-dim">Current</span>
            <span className="tabular-nums">{formatPrice(position.current_price)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-argus-text-dim">Shares</span>
            <span className="tabular-nums">
              {position.shares_remaining}/{position.shares_total}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-argus-text-dim flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Time
            </span>
            <span className="tabular-nums">{formatDuration(position.hold_duration_seconds)}</span>
          </div>
        </div>

        {/* Price levels */}
        <div className="grid grid-cols-3 gap-3 text-sm pt-2 border-t border-argus-border">
          <div className="flex flex-col items-center">
            <span className="text-argus-text-dim flex items-center gap-1">
              <Shield className="w-3 h-3 text-argus-loss" />
              Stop
            </span>
            <span className="tabular-nums text-argus-loss">{formatPrice(position.stop_price)}</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-argus-text-dim flex items-center gap-1">
              <Target className="w-3 h-3 text-argus-profit" />
              T1
            </span>
            <span className={`tabular-nums ${position.t1_filled ? 'text-argus-text-dim line-through' : 'text-argus-profit'}`}>
              {formatPrice(position.t1_price)}
            </span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-argus-text-dim flex items-center gap-1">
              <Target className="w-3 h-3 text-argus-profit" />
              T2
            </span>
            <span className="tabular-nums text-argus-profit">{formatPrice(position.t2_price)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
