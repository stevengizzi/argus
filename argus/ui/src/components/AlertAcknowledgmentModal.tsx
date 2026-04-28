/**
 * AlertAcknowledgmentModal: modal dialog for operator acknowledgment of a
 * critical alert.
 *
 * Posts to `POST /api/v1/alerts/{alert_id}/acknowledge` via the
 * `useAlerts` hook's `acknowledge` callback. Requires a reason of >=10
 * characters (matches backend validation in `AcknowledgeRequest`). Shows
 * the resulting audit-log id on success. Cancel leaves the alert active.
 *
 * Backend return contract (verified against `argus/api/routes/alerts.py`):
 *   - 200 normal/idempotent/late-ack — `AcknowledgeResult` with the
 *     ORIGINAL acknowledger info preserved on the idempotent path (so
 *     `result.acknowledged_by` is the prior operator, not the operator
 *     submitting now). The modal renders this as "previously acknowledged
 *     by <operator>" feedback.
 *   - 404 — alert vanished from history; hook returns `null`. The modal
 *     surfaces "Alert no longer active" rather than a hard error.
 *   - Other non-200 — hook throws; modal shows the error with a Retry.
 *
 * Sprint 31.91 Session 5d — D12 acknowledgment UI flow.
 */

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, X } from 'lucide-react';
import type { Alert, AcknowledgeResult } from '../hooks/useAlerts';
import { DURATION, EASE } from '../utils/motion';

const MIN_REASON_LENGTH = 10;
const MAX_REASON_LENGTH = 500;

interface Props {
  alert: Alert;
  operatorId: string;
  onClose: () => void;
  onSubmit: (
    reason: string,
    operatorId: string,
  ) => Promise<AcknowledgeResult | null>;
}

type SubmitOutcome =
  | { kind: 'first_ack'; result: AcknowledgeResult }
  | { kind: 'duplicate_ack'; result: AcknowledgeResult }
  | { kind: 'not_found' };

export function AlertAcknowledgmentModal({
  alert,
  operatorId,
  onClose,
  onSubmit,
}: Props) {
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<SubmitOutcome | null>(null);
  const reasonRef = useRef<HTMLTextAreaElement>(null);

  // Initial focus on the textarea — operator can start typing immediately.
  useEffect(() => {
    reasonRef.current?.focus();
  }, []);

  // Escape key closes the modal. Cancel-on-outcome-shown is allowed; the
  // operator confirms by reading the audit id and dismissing.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const trimmedLength = reason.trim().length;
  const canSubmit =
    trimmedLength >= MIN_REASON_LENGTH && !submitting && outcome === null;

  const classifyOutcome = (
    result: AcknowledgeResult | null,
  ): SubmitOutcome => {
    if (result === null) {
      return { kind: 'not_found' };
    }
    // Backend preserves the original acknowledger on the idempotent path.
    // If the returned `acknowledged_by` is not the operator who just
    // submitted, this submission was a duplicate — show "previously
    // acknowledged by <operator>" feedback.
    if (result.acknowledged_by && result.acknowledged_by !== operatorId) {
      return { kind: 'duplicate_ack', result };
    }
    return { kind: 'first_ack', result };
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await onSubmit(reason.trim(), operatorId);
      setOutcome(classifyOutcome(result));
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Acknowledge failed';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const renderOutcome = () => {
    if (!outcome) return null;
    if (outcome.kind === 'not_found') {
      return (
        <div
          role="status"
          aria-live="polite"
          className="text-amber-400 text-sm mt-2"
        >
          Alert no longer active (already auto-resolved or evicted).
        </div>
      );
    }
    if (outcome.kind === 'duplicate_ack') {
      return (
        <div
          role="status"
          aria-live="polite"
          className="text-argus-text text-sm mt-2"
        >
          Acknowledged (audit ID: {outcome.result.audit_id}). Previously
          acknowledged by <strong>{outcome.result.acknowledged_by}</strong>.
        </div>
      );
    }
    return (
      <div
        role="status"
        aria-live="polite"
        className="text-emerald-400 text-sm mt-2"
      >
        Acknowledged (audit ID: {outcome.result.audit_id}).
      </div>
    );
  };

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 bg-black/60 z-50"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: DURATION.fast }}
        onClick={onClose}
        data-testid="alert-ack-modal-backdrop"
      />
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-labelledby="alert-ack-modal-title"
          className="bg-argus-surface border border-argus-border rounded-lg w-full max-w-md shadow-xl"
          initial={{ scale: 0.95, y: 10 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 10 }}
          transition={{ duration: DURATION.normal, ease: EASE.out }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between p-4 border-b border-argus-border">
            <div className="flex items-center gap-2 text-argus-loss">
              <AlertTriangle className="w-5 h-5" aria-hidden="true" />
              <h2
                id="alert-ack-modal-title"
                className="text-lg font-semibold text-argus-text"
              >
                Acknowledge Alert
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="p-1 rounded hover:bg-argus-surface-2 transition-colors"
            >
              <X className="w-5 h-5 text-argus-text-dim" />
            </button>
          </div>

          <div className="p-4 space-y-3">
            <div className="text-sm">
              <div className="font-bold uppercase text-xs tracking-wide text-argus-loss">
                {alert.alert_type}
              </div>
              <div className="text-argus-text mt-1">{alert.message}</div>
            </div>

            <label className="block text-sm">
              <span className="text-argus-text-dim">
                Reason (required, &ge;{MIN_REASON_LENGTH} characters):
              </span>
              <textarea
                ref={reasonRef}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                minLength={MIN_REASON_LENGTH}
                maxLength={MAX_REASON_LENGTH}
                rows={4}
                disabled={submitting || outcome !== null}
                className="w-full mt-1 p-2 rounded border border-argus-border bg-argus-surface-2 text-argus-text disabled:opacity-60"
                aria-describedby="alert-ack-modal-counter"
              />
            </label>
            <div
              id="alert-ack-modal-counter"
              className="text-xs text-argus-text-dim text-right"
            >
              {trimmedLength}/{MAX_REASON_LENGTH}
            </div>

            {error && (
              <div role="alert" className="text-argus-loss text-sm">
                {error}.{' '}
                <button
                  type="button"
                  onClick={handleSubmit}
                  className="underline font-medium"
                >
                  Retry
                </button>
              </div>
            )}

            {renderOutcome()}
          </div>

          <div className="flex justify-end gap-3 p-4 border-t border-argus-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm rounded-md border border-argus-border bg-argus-surface hover:bg-argus-surface-2 transition-colors"
            >
              {outcome ? 'Close' : 'Cancel'}
            </button>
            {!outcome && (
              <button
                type="button"
                disabled={!canSubmit}
                onClick={handleSubmit}
                className="px-4 py-2 text-sm rounded-md text-white bg-argus-loss hover:bg-argus-loss/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'Acknowledging…' : 'Acknowledge'}
              </button>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
