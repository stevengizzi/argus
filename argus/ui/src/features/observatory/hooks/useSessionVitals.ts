/**
 * Hook for live session vitals — running totals, connection status,
 * closest miss, and top blocker.
 *
 * In live mode: subscribes to Observatory WebSocket for pipeline_update and
 * evaluation_summary messages, periodically fetches session-summary REST.
 * In debrief mode: fetches session-summary once for the selected date.
 *
 * Sprint 25, Session 9.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getObservatorySessionSummary, getToken } from '../../../api/client';
import type {
  ObservatoryBlockerEntry,
  ObservatoryClosestMissSummary,
  RegimeVectorSummary,
} from '../../../api/types';

export interface ConnectionStatus {
  databento: boolean;
  ibkr: boolean;
  ws: boolean;
}

export interface SessionMetrics {
  symbolsReceiving: number;
  totalEvaluations: number;
  totalSignals: number;
  totalTrades: number;
}

export interface UseSessionVitalsResult {
  metrics: SessionMetrics;
  connectionStatus: ConnectionStatus;
  closestMiss: ObservatoryClosestMissSummary | null;
  topBlocker: ObservatoryBlockerEntry | null;
  regimeVector: RegimeVectorSummary | null;
  marketTime: string;
  isLive: boolean;
}

function formatMarketTime(): string {
  return new Date().toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'America/New_York',
    hour12: true,
  }) + ' ET';
}

interface UseSessionVitalsOptions {
  date?: string;
}

export function useSessionVitals({
  date,
}: UseSessionVitalsOptions = {}): UseSessionVitalsResult {
  const isDebrief = date !== undefined;
  const queryClient = useQueryClient();

  // Running totals accumulated from WS deltas
  const [wsEvaluations, setWsEvaluations] = useState(0);
  const [wsSignals, setWsSignals] = useState(0);
  const [wsConnected, setWsConnected] = useState(false);

  // Market time updates every minute
  const [marketTime, setMarketTime] = useState(formatMarketTime);

  useEffect(() => {
    if (isDebrief) return;
    const timer = setInterval(() => setMarketTime(formatMarketTime()), 60_000);
    return () => clearInterval(timer);
  }, [isDebrief]);

  // REST session-summary query
  const { data: summaryData } = useQuery({
    queryKey: ['observatory', 'session-summary', date],
    queryFn: () => getObservatorySessionSummary(date),
    refetchInterval: isDebrief ? false : 10_000,
  });

  // Reset WS accumulators when switching modes or when summary refreshes
  const lastSummaryRef = useRef(summaryData);
  useEffect(() => {
    if (summaryData !== lastSummaryRef.current) {
      lastSummaryRef.current = summaryData;
      setWsEvaluations(0);
      setWsSignals(0);
    }
  }, [summaryData]);

  // Invalidate session-summary cache on WS updates
  const invalidateSessionSummary = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: ['observatory', 'session-summary'],
    });
  }, [queryClient]);

  // WebSocket subscription for live mode
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (isDebrief) {
      setWsConnected(false);
      return;
    }

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

        if (msg.type === 'auth_success') {
          setWsConnected(true);
          return;
        }

        if (msg.type === 'evaluation_summary') {
          const delta = msg.data;
          setWsEvaluations((prev) => prev + (delta.evaluations_count ?? 0));
          setWsSignals((prev) => prev + (delta.signals_count ?? 0));
          invalidateSessionSummary();
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    return () => {
      wsRef.current = null;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close(1000, 'Vitals unmount');
      }
    };
  }, [isDebrief, invalidateSessionSummary]);

  const baseEvaluations = summaryData?.total_evaluations ?? 0;
  const baseSignals = summaryData?.total_signals ?? 0;

  const metrics: SessionMetrics = {
    symbolsReceiving: summaryData?.symbols_evaluated ?? 0,
    totalEvaluations: baseEvaluations + wsEvaluations,
    totalSignals: baseSignals + wsSignals,
    totalTrades: summaryData?.total_trades ?? 0,
  };

  const connectionStatus: ConnectionStatus = {
    databento: wsConnected,
    ibkr: wsConnected,
    ws: wsConnected,
  };

  const closestMiss = summaryData?.closest_miss ?? null;

  const topBlocker =
    summaryData?.top_blockers && summaryData.top_blockers.length > 0
      ? summaryData.top_blockers[0]
      : null;

  const regimeVector = summaryData?.regime_vector_summary ?? null;

  return {
    metrics,
    connectionStatus,
    closestMiss,
    topBlocker,
    regimeVector,
    marketTime: isDebrief ? `Reviewing ${date}` : marketTime,
    isLive: !isDebrief,
  };
}
