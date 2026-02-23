/**
 * Hook for computing live equity and daily P&L from WebSocket price updates.
 *
 * Combines REST account data with WebSocket price overrides to provide
 * instant equity updates between REST polls. Returns null when data is
 * not yet available (fall back to REST data in that case).
 */

import { useAccount } from './useAccount';
import { usePositions } from './usePositions';
import { useLiveStore } from '../stores/live';

export interface LiveEquityData {
  equity: number;
  dailyPnl: number;
  dailyPnlPct: number;
}

/**
 * Compute live equity and daily P&L by applying WebSocket price updates
 * to the REST baseline.
 *
 * @returns Live equity data, or null if REST data not yet available
 */
export function useLiveEquity(): LiveEquityData | null {
  const { data: account } = useAccount();
  const { data: positionsData } = usePositions();
  const priceUpdates = useLiveStore((state) => state.priceUpdates);

  if (!account || !positionsData) return null;

  const positions = positionsData.positions;

  // Compute delta from WS price updates vs REST prices
  let delta = 0;
  for (const pos of positions) {
    const wsUpdate = priceUpdates[pos.symbol];
    if (wsUpdate !== undefined && pos.current_price) {
      // Calculate price difference based on position side
      const wsPriceDiff = pos.side === 'long'
        ? wsUpdate.price - pos.current_price
        : pos.current_price - wsUpdate.price;
      delta += wsPriceDiff * pos.shares_remaining;
    }
  }

  const liveEquity = account.equity + delta;
  const liveDailyPnl = account.daily_pnl + delta;

  // Calculate daily P&L percentage
  // Base equity (start of day) = current equity - daily P&L
  const baseEquity = account.equity - account.daily_pnl;
  const liveDailyPnlPct = baseEquity > 0 ? (liveDailyPnl / baseEquity) * 100 : 0;

  return {
    equity: liveEquity,
    dailyPnl: liveDailyPnl,
    dailyPnlPct: liveDailyPnlPct,
  };
}
