/**
 * Throttle override dialog modal.
 *
 * Allows operator to temporarily override throttle restrictions on a strategy.
 * Driven by orchestratorUI Zustand store.
 *
 * Styled with amber/warning severity to indicate risk control override.
 */

import { useState, useEffect } from 'react';
import { AlertTriangle, ShieldAlert, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useOrchestratorUI } from '../../stores/orchestratorUI';
import { useThrottleOverrideMutation } from '../../hooks/useOrchestratorMutations';
import { DURATION, EASE } from '../../utils/motion';
import { getStrategyDisplay } from '../../utils/strategyConfig';

const DURATION_OPTIONS = [
  { value: 30, label: '30 minutes' },
  { value: 60, label: '1 hour' },
  { value: 999, label: 'Rest of day' },
] as const;

const MIN_REASON_LENGTH = 10;

export function ThrottleOverrideDialog() {
  const { overrideDialogOpen, overrideTargetStrategy, closeOverrideDialog } =
    useOrchestratorUI();
  const overrideMutation = useThrottleOverrideMutation();

  // Form state
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog opens
  useEffect(() => {
    if (overrideDialogOpen) {
      setDurationMinutes(30);
      setReason('');
      setError(null);
    }
  }, [overrideDialogOpen]);

  const isReasonValid = reason.trim().length >= MIN_REASON_LENGTH;
  const canSubmit = isReasonValid && !overrideMutation.isPending;

  const handleSubmit = async () => {
    if (!canSubmit || !overrideTargetStrategy) return;

    try {
      await overrideMutation.mutateAsync({
        strategyId: overrideTargetStrategy,
        body: {
          duration_minutes: durationMinutes,
          reason: reason.trim(),
        },
      });
      closeOverrideDialog();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to override throttle'
      );
    }
  };

  const handleBackdropClick = () => {
    if (!overrideMutation.isPending) {
      closeOverrideDialog();
    }
  };

  return (
    <AnimatePresence>
      {overrideDialogOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/60 z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: DURATION.fast }}
            onClick={handleBackdropClick}
          />

          {/* Modal */}
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="bg-argus-surface border-2 border-amber-500/40 rounded-lg w-full max-w-md shadow-xl"
              initial={{ scale: 0.95, y: 10 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 10 }}
              transition={{ duration: DURATION.normal, ease: EASE.out }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-amber-500/20">
                <div className="flex items-center gap-2 text-amber-400">
                  <ShieldAlert className="w-5 h-5" />
                  <h2 className="text-lg font-semibold">Override Throttle</h2>
                </div>
                <button
                  onClick={closeOverrideDialog}
                  disabled={overrideMutation.isPending}
                  className="p-1 rounded hover:bg-argus-surface-2 transition-colors disabled:opacity-50"
                >
                  <X className="w-5 h-5 text-argus-text-dim" />
                </button>
              </div>

              {/* Content */}
              <div className="p-4 space-y-4">
                {/* Strategy name */}
                {overrideTargetStrategy && (
                  <div className="text-sm">
                    <span className="text-argus-text-dim">Strategy: </span>
                    <span className="text-argus-text font-medium">
                      {getStrategyDisplay(overrideTargetStrategy).name}
                    </span>
                  </div>
                )}

                {/* Warning message */}
                <div className="flex items-start gap-2 p-3 rounded-md bg-amber-500/10 border border-amber-500/20">
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <p className="text-sm text-amber-200">
                    This temporarily overrides performance-based risk controls.
                    The strategy will resume accepting new trades.
                  </p>
                </div>

                {/* Duration select */}
                <div>
                  <label className="block text-sm text-argus-text-dim mb-1.5">
                    Override Duration
                  </label>
                  <select
                    value={durationMinutes}
                    onChange={(e) => setDurationMinutes(Number(e.target.value))}
                    disabled={overrideMutation.isPending}
                    className="w-full px-3 py-2 text-sm rounded-md border border-argus-border bg-argus-surface-2 text-argus-text focus:outline-none focus:ring-1 focus:ring-amber-500/50 disabled:opacity-50"
                  >
                    {DURATION_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Reason textarea */}
                <div>
                  <label className="block text-sm text-argus-text-dim mb-1.5">
                    Reason for Override{' '}
                    <span className="text-amber-400">*</span>
                  </label>
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    disabled={overrideMutation.isPending}
                    placeholder="Why are you overriding? (required, min 10 characters)"
                    rows={3}
                    className="w-full px-3 py-2 text-sm rounded-md border border-argus-border bg-argus-surface-2 text-argus-text placeholder:text-argus-text-dim/50 focus:outline-none focus:ring-1 focus:ring-amber-500/50 resize-none disabled:opacity-50"
                  />
                  <p className="text-xs text-argus-text-dim mt-1">
                    {reason.trim().length}/{MIN_REASON_LENGTH} characters
                    minimum
                  </p>
                </div>

                {/* Error message */}
                {error && (
                  <div className="p-3 rounded-md bg-argus-loss/10 text-argus-loss text-sm border border-argus-loss/20">
                    {error}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 p-4 border-t border-argus-border">
                <button
                  onClick={closeOverrideDialog}
                  disabled={overrideMutation.isPending}
                  className="px-4 py-2 text-sm rounded-md border border-argus-border bg-argus-surface hover:bg-argus-surface-2 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={!canSubmit}
                  className="px-4 py-2 text-sm rounded-md bg-amber-500 hover:bg-amber-500/80 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {overrideMutation.isPending
                    ? 'Overriding...'
                    : 'Confirm Override'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
