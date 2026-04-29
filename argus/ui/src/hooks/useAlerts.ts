/**
 * useAlerts: TanStack Query + WebSocket hybrid hook for alert observability.
 *
 * Initial state via REST (`GET /api/v1/alerts/active`); real-time updates
 * via WebSocket (`/ws/v1/alerts`) following the same JWT-auth pattern as
 * observatory_ws and arena_ws (auth message first, auth_success then
 * snapshot then state-change deltas).
 *
 * Reconnect resilience: WebSocket disconnect flips connectionStatus to
 * "disconnected" and the REST query takes over with a 5s polling
 * interval; on reconnect, refetch() is invoked from inside the auth_success
 * branch so the operator sees a consistent state immediately. The backend
 * also pushes a fresh snapshot frame after auth_success; whichever
 * response arrives last wins (last-write-wins via TanStack Query cache).
 *
 * Sprint 31.91 Session 5c — D11 alert observability frontend.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, useCallback } from 'react';
import { getToken } from '../api/client';

// ---------------------------------------------------------------------------
// Public types — mirror argus/api/routes/alerts.py::AlertResponse
// ---------------------------------------------------------------------------

export type AlertSeverity = 'critical' | 'warning' | 'info';

/** Mirrors `AlertLifecycleState` enum in argus/core/health.py. */
export type AlertState = 'active' | 'acknowledged' | 'archived';

export type ConnectionStatus = 'loading' | 'connected' | 'disconnected' | 'error';

export interface Alert {
  alert_id: string;
  alert_type: string;
  severity: AlertSeverity;
  source: string;
  message: string;
  metadata: Record<string, unknown>;
  state: AlertState;
  created_at_utc: string;
  acknowledged_at_utc: string | null;
  acknowledged_by: string | null;
  archived_at_utc: string | null;
  acknowledgment_reason: string | null;
}

export interface AcknowledgeResult {
  alert_id: string;
  acknowledged_at_utc: string;
  acknowledged_by: string;
  reason: string;
  audit_id: number;
  state: AlertState;
}

/** One row of the `alert_acknowledgment_audit` log. */
export interface AlertAuditEntry {
  audit_id: number;
  timestamp_utc: string;
  alert_id: string;
  operator_id: string;
  reason: string;
  /** "ack" | "duplicate_ack" | "late_ack" — backend-defined string. */
  audit_kind: string;
}

/** Inclusive ISO-8601 UTC range. `to` filtered client-side. */
export interface AlertHistoryRange {
  from: string;
  to: string;
}

export interface UseAlertsResult {
  alerts: Alert[];
  connectionStatus: ConnectionStatus;
  acknowledge: (
    alert_id: string,
    reason: string,
    operator_id: string,
  ) => Promise<AcknowledgeResult | null>;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ALERTS_QUERY_KEY = ['alerts', 'active'] as const;
const REST_DISCONNECTED_REFETCH_MS = 5_000;

// ---------------------------------------------------------------------------
// REST helpers
// ---------------------------------------------------------------------------

async function fetchActiveAlerts(): Promise<Alert[]> {
  const token = getToken();
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const response = await fetch('/api/v1/alerts/active', { headers });
  if (!response.ok) {
    throw new Error(`Failed to fetch active alerts: HTTP ${response.status}`);
  }
  return (await response.json()) as Alert[];
}

async function postAcknowledge(
  alert_id: string,
  reason: string,
  operator_id: string,
): Promise<AcknowledgeResult | null> {
  const token = getToken();
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const response = await fetch(
    `/api/v1/alerts/${encodeURIComponent(alert_id)}/acknowledge`,
    {
      method: 'POST',
      headers,
      body: JSON.stringify({ reason, operator_id }),
    },
  );

  // 200: normal/idempotent/late-ack — backend returns AcknowledgeResult.
  // 404: alert vanished from history (rare). Surface as null so the UI
  //      can decide whether to retry. Banner just relies on the WS push
  //      to drop it from the list.
  // Other 4xx (e.g., 422 validation): propagate so callers can show error.
  if (response.status === 200) {
    return (await response.json()) as AcknowledgeResult;
  }
  if (response.status === 404) {
    return null;
  }
  throw new Error(`Acknowledge failed: HTTP ${response.status}`);
}

// ---------------------------------------------------------------------------
// WebSocket message types (server → client)
// ---------------------------------------------------------------------------

interface WsAuthSuccessMessage {
  type: 'auth_success';
  timestamp: string;
}

interface WsSnapshotMessage {
  type: 'snapshot';
  timestamp: string;
  alerts: Alert[];
}

interface WsAlertDeltaMessage {
  type:
    | 'alert_active'
    | 'alert_acknowledged'
    | 'alert_auto_resolved'
    | 'alert_archived';
  timestamp: string;
  alert: Alert;
}

type WsMessage =
  | WsAuthSuccessMessage
  | WsSnapshotMessage
  | WsAlertDeltaMessage
  | { type: string; [key: string]: unknown };

// ---------------------------------------------------------------------------
// Cache merge helpers
// ---------------------------------------------------------------------------

/** Active alerts only (active + acknowledged); archived alerts removed. */
function isVisible(alert: Alert): boolean {
  return alert.state === 'active' || alert.state === 'acknowledged';
}

function upsertAlert(prev: Alert[] | undefined, next: Alert): Alert[] {
  const list = prev ?? [];
  const idx = list.findIndex((a) => a.alert_id === next.alert_id);
  if (idx === -1) {
    return isVisible(next) ? [...list, next] : list;
  }
  if (!isVisible(next)) {
    return list.filter((a) => a.alert_id !== next.alert_id);
  }
  const copy = list.slice();
  copy[idx] = next;
  return copy;
}

function removeAlert(prev: Alert[] | undefined, alert_id: string): Alert[] {
  return (prev ?? []).filter((a) => a.alert_id !== alert_id);
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAlerts(): UseAlertsResult {
  const queryClient = useQueryClient();
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('loading');
  const wsRef = useRef<WebSocket | null>(null);
  // Tracks whether we've previously been disconnected — used to gate the
  // recover-via-REST refetch on auth_success so the initial connect does
  // not double-fetch (backend always sends a snapshot frame after auth).
  const wasDisconnectedRef = useRef(false);

  // REST query: provides initial state and acts as polling fallback while
  // the WebSocket is disconnected.
  const { data: alerts = [], refetch } = useQuery<Alert[]>({
    queryKey: ALERTS_QUERY_KEY,
    queryFn: fetchActiveAlerts,
    refetchInterval:
      connectionStatus === 'disconnected' || connectionStatus === 'error'
        ? REST_DISCONNECTED_REFETCH_MS
        : false,
  });

  useEffect(() => {
    const token = getToken();
    if (!token) {
      // No auth token available — REST query will surface the 401; do not
      // open a WebSocket that cannot authenticate.
      setConnectionStatus('error');
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/v1/alerts`;

    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
    } catch {
      setConnectionStatus('error');
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'auth', token }));
    };

    ws.onmessage = (event: MessageEvent<string>) => {
      let msg: WsMessage;
      try {
        msg = JSON.parse(event.data) as WsMessage;
      } catch {
        return;
      }

      switch (msg.type) {
        case 'auth_success': {
          setConnectionStatus('connected');
          // Resync state via REST ONLY on reconnect (recovery from a
          // prior disconnect). Initial connect skips the refetch because
          // the backend's snapshot frame, which always follows
          // auth_success, already provides the authoritative state. This
          // avoids double-fetching on first mount.
          if (wasDisconnectedRef.current) {
            wasDisconnectedRef.current = false;
            void refetch();
          }
          break;
        }
        case 'snapshot': {
          const snap = msg as WsSnapshotMessage;
          queryClient.setQueryData<Alert[]>(
            ALERTS_QUERY_KEY,
            snap.alerts.filter(isVisible),
          );
          break;
        }
        case 'alert_active':
        case 'alert_acknowledged':
        case 'alert_auto_resolved': {
          const delta = msg as WsAlertDeltaMessage;
          queryClient.setQueryData<Alert[]>(ALERTS_QUERY_KEY, (prev) =>
            upsertAlert(prev, delta.alert),
          );
          break;
        }
        case 'alert_archived': {
          // Defensive: backend documents this frame type but does not
          // currently emit it (auto-resolution emits alert_auto_resolved).
          // If a future producer fires alert_archived, drop the alert.
          const delta = msg as WsAlertDeltaMessage;
          const id = delta.alert?.alert_id;
          if (id) {
            queryClient.setQueryData<Alert[]>(ALERTS_QUERY_KEY, (prev) =>
              removeAlert(prev, id),
            );
          }
          break;
        }
        default:
          break;
      }
    };

    ws.onerror = () => {
      wasDisconnectedRef.current = true;
      setConnectionStatus('error');
    };

    ws.onclose = () => {
      wasDisconnectedRef.current = true;
      setConnectionStatus('disconnected');
    };

    return () => {
      wsRef.current = null;
      if (
        ws.readyState === WebSocket.OPEN ||
        ws.readyState === WebSocket.CONNECTING
      ) {
        ws.close(1000, 'useAlerts unmount');
      }
    };
  }, [queryClient, refetch]);

  const acknowledge = useCallback(
    async (
      alert_id: string,
      reason: string,
      operator_id: string,
    ): Promise<AcknowledgeResult | null> => {
      return postAcknowledge(alert_id, reason, operator_id);
    },
    [],
  );

  return { alerts, connectionStatus, acknowledge };
}

// ---------------------------------------------------------------------------
// Historical alerts (Sprint 31.91 Session 5e — D13 Observatory panel)
// ---------------------------------------------------------------------------

async function fetchAlertHistory(from: string): Promise<Alert[]> {
  const token = getToken();
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  // Backend supports `since` only (5a.1 surface). `to` filtered
  // client-side until the backend grows an `until` parameter.
  const url = `/api/v1/alerts/history?since=${encodeURIComponent(from)}`;
  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`Failed to fetch alert history: HTTP ${response.status}`);
  }
  return (await response.json()) as Alert[];
}

/**
 * `useAlertHistory`: TanStack Query hook for the historical alert window.
 *
 * Backend's `/history` endpoint accepts only `since`; this hook fetches
 * with `since=range.from` and applies the `range.to` upper bound
 * client-side. If/when the backend grows `until`, the client-side filter
 * becomes a no-op and the call site does not change.
 */
export function useAlertHistory(range: AlertHistoryRange) {
  return useQuery<Alert[]>({
    queryKey: ['alerts', 'history', range.from, range.to],
    queryFn: async () => {
      const all = await fetchAlertHistory(range.from);
      // Inclusive upper bound by created_at_utc (ISO-8601 UTC).
      return all.filter((a) => a.created_at_utc <= range.to);
    },
    enabled: Boolean(range.from && range.to),
  });
}

// ---------------------------------------------------------------------------
// Audit trail (per-alert acknowledgment history)
// ---------------------------------------------------------------------------

async function fetchAuditTrail(alert_id: string): Promise<AlertAuditEntry[]> {
  const token = getToken();
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const response = await fetch(
    `/api/v1/alerts/${encodeURIComponent(alert_id)}/audit`,
    { headers },
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch audit trail: HTTP ${response.status}`);
  }
  return (await response.json()) as AlertAuditEntry[];
}

/**
 * `useAlertAuditTrail`: per-alert acknowledgment history.
 *
 * Returns an empty list for alerts that were never acknowledged. Used by
 * `AlertDetailView` in the Observatory panel.
 */
export function useAlertAuditTrail(alert_id: string | null) {
  return useQuery<AlertAuditEntry[]>({
    queryKey: ['alerts', alert_id, 'audit'],
    queryFn: () => fetchAuditTrail(alert_id as string),
    enabled: alert_id !== null,
  });
}
