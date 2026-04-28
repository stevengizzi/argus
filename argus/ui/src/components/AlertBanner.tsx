/**
 * AlertBanner: persistent banner for active critical alerts.
 *
 * Renders only when at least one alert is `severity === "critical"` AND
 * `state === "active"`. When an alert is acknowledged or auto-resolved, the
 * WebSocket pushes a state delta, the TanStack Query cache updates, this
 * component re-renders, and — if no critical-active alerts remain — the
 * banner unmounts. The 1s disappearance budget covers WS round-trip plus
 * a React re-render.
 *
 * Severity-rendering decision (Sprint 31.91 Session 5c): banner displays
 * `critical` only. `warning` and `info` are routed to the toast surface
 * landing in Session 5d. This matches `AlertsConfig.acknowledgment_*`
 * intent: only `critical` requires operator acknowledgment.
 *
 * Mounted on `DashboardPage.tsx` for 5c; Session 5e relocates the mount
 * to `Layout.tsx` for cross-page persistence.
 */

import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { useAlerts } from '../hooks/useAlerts';

const ACK_REASON_DEFAULT = 'Acknowledged from Dashboard banner';
const ACK_OPERATOR_ID = 'operator';

export function AlertBanner() {
  const { alerts, acknowledge } = useAlerts();
  const [acking, setAcking] = useState<string | null>(null);

  const criticalActive = alerts.filter(
    (a) => a.severity === 'critical' && a.state === 'active',
  );

  if (criticalActive.length === 0) {
    return null;
  }

  // Most-recently-emitted alert by created_at_utc — that's the headline.
  // Using ISO-8601 string compare is correct because all timestamps are UTC.
  const sorted = [...criticalActive].sort((a, b) =>
    a.created_at_utc < b.created_at_utc ? 1 : -1,
  );
  const top = sorted[0];
  const others = criticalActive.length - 1;

  const handleAck = async () => {
    if (acking) return;
    setAcking(top.alert_id);
    try {
      await acknowledge(top.alert_id, ACK_REASON_DEFAULT, ACK_OPERATOR_ID);
    } catch {
      // Swallow — error UI lands in 5d's modal. The WS push will drop the
      // alert from the list if the ack succeeded; if it failed, the
      // banner stays visible and the operator can retry.
    } finally {
      setAcking(null);
    }
  };

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="bg-red-600 border border-red-700 text-white px-4 py-3 rounded-lg shadow-lg"
    >
      <div className="flex items-center gap-3">
        <AlertTriangle className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
        <span className="font-bold uppercase text-xs tracking-wide">
          Critical
        </span>
        <span className="text-sm flex-1 truncate" title={top.message}>
          {top.message}
        </span>
        {others > 0 && (
          <span className="text-xs text-red-200 whitespace-nowrap">
            +{others} more
          </span>
        )}
        <button
          type="button"
          onClick={handleAck}
          disabled={acking === top.alert_id}
          className="bg-white text-red-700 hover:bg-red-50 disabled:opacity-60 disabled:cursor-not-allowed text-xs font-semibold px-3 py-1.5 rounded transition-colors"
        >
          {acking === top.alert_id ? 'Acknowledging…' : 'Acknowledge'}
        </button>
      </div>
    </div>
  );
}
