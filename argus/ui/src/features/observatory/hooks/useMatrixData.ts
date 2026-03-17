/**
 * Data hook for the Matrix view — fetches closest-miss data via TanStack Query,
 * subscribes to Observatory WebSocket for live updates, and maintains sorted rows.
 *
 * Sort: conditions_passed descending, then alphabetical symbol as tiebreaker.
 * In debrief mode (date provided): fetch once, no WS subscription.
 *
 * Sprint 25, Session 5b.
 */

import { useEffect, useCallback, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getObservatoryClosestMisses } from '../../../api/client';
import { getToken } from '../../../api/client';
import type { ObservatoryClosestMissEntry } from '../../../api/types';
import { PIPELINE_TIERS } from './useObservatoryKeyboard';

function tierIndexToKey(index: number): string {
  const tier = PIPELINE_TIERS[index];
  return tier.toLowerCase().replace('-', '_');
}

function sortEntries(
  items: ObservatoryClosestMissEntry[],
): ObservatoryClosestMissEntry[] {
  return [...items].sort((a, b) => {
    const scoreDiff = b.conditions_passed - a.conditions_passed;
    if (scoreDiff !== 0) return scoreDiff;
    return a.symbol.localeCompare(b.symbol);
  });
}

interface UseMatrixDataOptions {
  tierIndex: number;
  limit?: number;
  date?: string;
}

interface UseMatrixDataResult {
  rows: ObservatoryClosestMissEntry[];
  isLoading: boolean;
  error: Error | null;
  highlightedSymbol: string | null;
  setHighlightedSymbol: (symbol: string | null) => void;
}

export function useMatrixData({
  tierIndex,
  limit = 100,
  date,
}: UseMatrixDataOptions): UseMatrixDataResult {
  const tierKey = tierIndexToKey(tierIndex);
  const isDebrief = date !== undefined;
  const queryClient = useQueryClient();

  const [highlightedSymbol, setHighlightedSymbol] = useState<string | null>(
    null,
  );

  const { data, isLoading, error } = useQuery({
    queryKey: ['observatory', 'closest-misses', tierKey, date],
    queryFn: () => getObservatoryClosestMisses(tierKey, limit, date),
    refetchInterval: isDebrief ? false : 5_000,
  });

  const rows = useMemo(
    () => sortEntries(data?.items ?? []),
    [data],
  );

  // WebSocket subscription for live cache invalidation (not in debrief mode)
  const wsRef = useRef<WebSocket | null>(null);

  const invalidateCache = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: ['observatory', 'closest-misses', tierKey],
    });
  }, [queryClient, tierKey]);

  useEffect(() => {
    if (isDebrief) return;

    const token = getToken();
    if (!token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/v1/observatory`;

    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
    } catch {
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'auth', token }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        // On tier transitions or evaluation summaries, refetch closest-misses
        if (
          msg.type === 'tier_transition' ||
          msg.type === 'evaluation_summary'
        ) {
          invalidateCache();
        }
      } catch {
        // Ignore malformed messages
      }
    };

    return () => {
      wsRef.current = null;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close(1000, 'Matrix unmount');
      }
    };
  }, [isDebrief, tierKey, invalidateCache]);

  return {
    rows,
    isLoading,
    error: error as Error | null,
    highlightedSymbol,
    setHighlightedSymbol,
  };
}
