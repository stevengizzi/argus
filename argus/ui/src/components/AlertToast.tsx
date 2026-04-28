/**
 * AlertToast + AlertToastStack: cross-page critical-alert notification
 * surface.
 *
 * `AlertToastStack` consumes `useAlerts` and renders one `AlertToast` per
 * active critical alert, capped at MAX_TOAST_QUEUE. It also owns the
 * single-modal state so clicking "Acknowledge" on any toast opens
 * `AlertAcknowledgmentModal` for that alert.
 *
 * Auto-dismiss on auto-resolve: the stack is a pure render of
 * `useAlerts().alerts` filtered to critical+active. When the backend
 * pushes `alert_auto_resolved` or `alert_acknowledged`, the hook state
 * updates, this component re-renders, and the toast unmounts. Same
 * mechanism as Session 5c's AlertBanner.
 *
 * Queue overflow: when more than MAX_TOAST_QUEUE critical alerts are
 * active, only the most recent MAX_TOAST_QUEUE are rendered. The dropped
 * alerts remain in the underlying `useAlerts` state and will be visible
 * in the Observatory panel landing in Session 5e. Operator-comfort
 * decision: 6+ simultaneous critical toasts is a panic state and
 * showing all of them helps no one.
 *
 * Mount: 5d mounts on `DashboardPage.tsx` alongside `AlertBanner`. 5e
 * relocates the mount to `Layout.tsx` for cross-page persistence.
 *
 * Sprint 31.91 Session 5d — D12 toast notification system.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';
import type { Alert } from '../hooks/useAlerts';
import { useAlerts } from '../hooks/useAlerts';
import { AlertAcknowledgmentModal } from './AlertAcknowledgmentModal';
import { DURATION, EASE } from '../utils/motion';

const MAX_TOAST_QUEUE = 5;
const ACK_OPERATOR_ID = 'operator';

export function AlertToastStack() {
  const { alerts, acknowledge } = useAlerts();
  const [modalAlert, setModalAlert] = useState<Alert | null>(null);

  // Critical-active alerts, oldest-first by created_at_utc. ISO-8601 UTC
  // strings compare lexicographically — same approach used by AlertBanner.
  const activeCritical = [...alerts]
    .filter((a) => a.severity === 'critical' && a.state === 'active')
    .sort((a, b) =>
      a.created_at_utc < b.created_at_utc
        ? -1
        : a.created_at_utc > b.created_at_utc
          ? 1
          : 0,
    );

  // When queue exceeds cap, drop the OLDEST (operator-comfort decision —
  // newest events are the most actionable). `slice(-MAX)` keeps the last
  // (newest) MAX entries; `.reverse()` puts the newest visually on top.
  const visible = activeCritical.slice(-MAX_TOAST_QUEUE).reverse();

  return (
    <>
      <div
        role="region"
        aria-label="Alert notifications"
        className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-96 max-w-[calc(100vw-2rem)] pointer-events-none"
      >
        <AnimatePresence initial={false}>
          {visible.map((alert) => (
            <AlertToast
              key={alert.alert_id}
              alert={alert}
              onAcknowledge={() => setModalAlert(alert)}
            />
          ))}
        </AnimatePresence>
      </div>
      {modalAlert && (
        <AlertAcknowledgmentModal
          alert={modalAlert}
          operatorId={ACK_OPERATOR_ID}
          onClose={() => setModalAlert(null)}
          onSubmit={(reason, operatorId) =>
            acknowledge(modalAlert.alert_id, reason, operatorId)
          }
        />
      )}
    </>
  );
}

interface AlertToastProps {
  alert: Alert;
  onAcknowledge: () => void;
}

export function AlertToast({ alert, onAcknowledge }: AlertToastProps) {
  return (
    <motion.div
      role="status"
      aria-live="polite"
      data-testid={`alert-toast-${alert.alert_id}`}
      className="bg-argus-loss text-white p-3 rounded-lg shadow-xl border border-red-700 pointer-events-auto"
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 40 }}
      transition={{ duration: DURATION.normal, ease: EASE.out }}
    >
      <div className="flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <div className="flex-1 min-w-0">
          <div className="font-bold uppercase text-xs tracking-wide">
            {alert.alert_type}
          </div>
          <div className="text-sm mt-1 break-words">{alert.message}</div>
          <button
            type="button"
            onClick={onAcknowledge}
            className="mt-2 bg-white text-red-700 hover:bg-red-50 text-xs font-semibold px-3 py-1 rounded transition-colors"
          >
            Acknowledge
          </button>
        </div>
      </div>
    </motion.div>
  );
}
