/**
 * Side-effect hook that merges WebSocket position.updated events into the
 * usePositions query cache, providing near-real-time P&L/R updates without
 * full REST refetches.
 *
 * Sprint 29.5 Session 4.
 */

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getWebSocketClient } from '../api/ws';
import type { WebSocketMessage } from '../api/types';
import type { PositionsResponse } from '../api/types';

/** Fields we extract from a position.updated WS payload. */
interface PositionUpdatePayload {
  symbol: string;
  current_price: number;
  unrealized_pnl: number;
  r_multiple: number;
}

/**
 * Type-guard: returns true if `data` looks like a valid position update.
 */
function isPositionUpdate(data: unknown): data is PositionUpdatePayload {
  if (typeof data !== 'object' || data === null) return false;
  const d = data as Record<string, unknown>;
  return (
    typeof d.symbol === 'string' &&
    typeof d.current_price === 'number' &&
    typeof d.unrealized_pnl === 'number' &&
    typeof d.r_multiple === 'number'
  );
}

/**
 * Subscribe to `position.updated` WebSocket messages and merge live fields
 * (current_price, unrealized_pnl, r_multiple_current) into every matching
 * position across all cached usePositions queries.
 *
 * This is a side-effect-only hook — it returns nothing. The consuming
 * component reads updated data through the normal usePositions() hook.
 */
export function usePositionUpdates(): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    const client = getWebSocketClient();

    const unsubscribe = client.onMessage((message: WebSocketMessage) => {
      if (message.type !== 'position.updated') return;
      if (!isPositionUpdate(message.data)) return;

      const { symbol, current_price, unrealized_pnl, r_multiple } = message.data;

      // Update all cached positions queries (any strategy_id variant)
      queryClient.setQueriesData<PositionsResponse>(
        { queryKey: ['positions'] },
        (old) => {
          if (!old) return old;

          const hasMatch = old.positions.some((p) => p.symbol === symbol);
          if (!hasMatch) return old;

          return {
            ...old,
            positions: old.positions.map((pos) => {
              if (pos.symbol !== symbol) return pos;
              return {
                ...pos,
                current_price,
                unrealized_pnl,
                r_multiple_current: r_multiple,
              };
            }),
          };
        },
      );
    });

    return unsubscribe;
  }, [queryClient]);
}
