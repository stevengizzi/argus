/**
 * Open positions table with real-time price updates via WebSocket.
 *
 * Merges REST data with WebSocket price updates. Responsive columns
 * for desktop, tablet, and phone layouts. P&L values flash on change.
 */

import { useMemo } from 'react';
import { TrendingUp } from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { LoadingState } from '../../components/LoadingState';
import { EmptyState } from '../../components/EmptyState';
import { PnlValue } from '../../components/PnlValue';
import { Badge } from '../../components/Badge';
import { usePositions } from '../../hooks/usePositions';
import { useLiveStore } from '../../stores/live';
import { formatPrice, formatDuration } from '../../utils/format';
import type { Position } from '../../api/types';

interface EnrichedPosition extends Position {
  livePrice: number;
  livePnl: number;
  liveR: number;
}

export function OpenPositions() {
  const { data, isLoading, error } = usePositions();
  const priceUpdates = useLiveStore((state) => state.priceUpdates);

  // Extract positions array for stable dependency
  const positions = data?.positions;

  // Merge REST positions with WebSocket price updates
  const enrichedPositions = useMemo<EnrichedPosition[]>(() => {
    if (!positions) return [];

    return positions.map((pos) => {
      const wsUpdate = priceUpdates[pos.symbol];

      // Use WebSocket price if available and newer
      const livePrice = wsUpdate?.price ?? pos.current_price;

      // Recalculate P&L with live price
      const priceDiff = pos.side === 'long'
        ? livePrice - pos.entry_price
        : pos.entry_price - livePrice;
      const livePnl = priceDiff * pos.shares_remaining;

      // Recalculate R-multiple with live price
      const stopDiff = Math.abs(pos.entry_price - pos.stop_price);
      const liveR = stopDiff > 0 ? priceDiff / stopDiff : 0;

      return {
        ...pos,
        livePrice,
        livePnl,
        liveR,
      };
    });
  }, [positions, priceUpdates]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Open Positions" />
        <LoadingState message="Loading positions..." />
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader title="Open Positions" />
        <div className="text-argus-loss text-sm">Failed to load positions</div>
      </Card>
    );
  }

  if (enrichedPositions.length === 0) {
    return (
      <Card>
        <CardHeader title="Open Positions" subtitle="0 positions" />
        <EmptyState
          icon={TrendingUp}
          message="No open positions — system is monitoring for signals"
        />
      </Card>
    );
  }

  return (
    <Card noPadding>
      <div className="p-4 pb-0">
        <CardHeader
          title="Open Positions"
          subtitle={`${enrichedPositions.length} position${enrichedPositions.length !== 1 ? 's' : ''}`}
        />
      </div>

      {/* Desktop table (lg and up) */}
      <div className="hidden lg:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-argus-surface-2 text-argus-text-dim text-xs uppercase tracking-wider">
              <th className="px-4 py-2 text-left font-medium">Symbol</th>
              <th className="px-4 py-2 text-left font-medium">Side</th>
              <th className="px-4 py-2 text-right font-medium">Entry</th>
              <th className="px-4 py-2 text-right font-medium">Current</th>
              <th className="px-4 py-2 text-right font-medium">P&L</th>
              <th className="px-4 py-2 text-right font-medium">R</th>
              <th className="px-4 py-2 text-right font-medium">Time</th>
              <th className="px-4 py-2 text-right font-medium">Stop</th>
              <th className="px-4 py-2 text-right font-medium">T1</th>
              <th className="px-4 py-2 text-right font-medium">T2</th>
              <th className="px-4 py-2 text-center font-medium">T1 Hit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-argus-border">
            {enrichedPositions.map((pos) => (
              <tr key={pos.position_id} className="hover:bg-argus-bg/50">
                <td className="px-4 py-3 font-medium text-argus-text">{pos.symbol}</td>
                <td className="px-4 py-3">
                  <Badge variant={pos.side === 'long' ? 'success' : 'danger'}>
                    {pos.side.toUpperCase()}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-right tabular-nums">{formatPrice(pos.entry_price)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{formatPrice(pos.livePrice)}</td>
                <td className="px-4 py-3 text-right">
                  <PnlValue value={pos.livePnl} size="sm" flash />
                </td>
                <td className="px-4 py-3 text-right">
                  <PnlValue value={pos.liveR} format="r-multiple" size="sm" flash />
                </td>
                <td className="px-4 py-3 text-right text-argus-text-dim tabular-nums">
                  {formatDuration(pos.hold_duration_seconds)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-argus-loss">
                  {formatPrice(pos.stop_price)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-argus-profit">
                  {formatPrice(pos.t1_price)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-argus-profit">
                  {formatPrice(pos.t2_price)}
                </td>
                <td className="px-4 py-3 text-center">
                  {pos.t1_filled ? (
                    <span className="text-argus-profit">Yes</span>
                  ) : (
                    <span className="text-argus-text-dim">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Tablet table (md to lg) */}
      <div className="hidden md:block lg:hidden overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-argus-surface-2 text-argus-text-dim text-xs uppercase tracking-wider">
              <th className="px-4 py-2 text-left font-medium">Symbol</th>
              <th className="px-4 py-2 text-right font-medium">Entry</th>
              <th className="px-4 py-2 text-right font-medium">Current</th>
              <th className="px-4 py-2 text-right font-medium">P&L</th>
              <th className="px-4 py-2 text-right font-medium">R</th>
              <th className="px-4 py-2 text-right font-medium">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-argus-border">
            {enrichedPositions.map((pos) => (
              <tr key={pos.position_id} className="hover:bg-argus-bg/50">
                <td className="px-4 py-3 font-medium text-argus-text">{pos.symbol}</td>
                <td className="px-4 py-3 text-right tabular-nums">{formatPrice(pos.entry_price)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{formatPrice(pos.livePrice)}</td>
                <td className="px-4 py-3 text-right">
                  <PnlValue value={pos.livePnl} size="sm" flash />
                </td>
                <td className="px-4 py-3 text-right">
                  <PnlValue value={pos.liveR} format="r-multiple" size="sm" flash />
                </td>
                <td className="px-4 py-3 text-right text-argus-text-dim tabular-nums">
                  {formatDuration(pos.hold_duration_seconds)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Phone layout (compact cards) */}
      <div className="md:hidden divide-y divide-argus-border">
        {enrichedPositions.map((pos) => (
          <div key={pos.position_id} className="p-4 hover:bg-argus-bg/50">
            <div className="flex items-center justify-between">
              <span className="font-medium text-argus-text">{pos.symbol}</span>
              <PnlValue value={pos.livePnl} size="sm" flash />
            </div>
            <div className="flex items-center justify-between mt-1 text-sm">
              <span className="text-argus-text-dim">
                {pos.side.toUpperCase()} @ {formatPrice(pos.entry_price)}
              </span>
              <PnlValue value={pos.liveR} format="r-multiple" size="sm" flash />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
