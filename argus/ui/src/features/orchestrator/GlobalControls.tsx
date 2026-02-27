/**
 * Global controls section for the Orchestrator page.
 *
 * Provides buttons for:
 * - Force rebalance (recalculate allocations)
 * - Emergency pause all strategies
 * - Emergency flatten all positions
 *
 * Each action requires confirmation via modal dialog.
 */

import { useState } from 'react';
import {
  AlertTriangle,
  PauseCircle,
  RefreshCcw,
  XCircle,
  X,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import {
  useEmergencyFlatten,
  useEmergencyPauseAll,
} from '../../hooks/useControls';
import { useRebalanceMutation } from '../../hooks/useOrchestratorMutations';
import { DURATION, EASE } from '../../utils/motion';

type ModalVariant = 'info' | 'warning' | 'danger';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText: string;
  isLoading: boolean;
  variant: ModalVariant;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmModal({
  isOpen,
  title,
  message,
  confirmText,
  isLoading,
  variant,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const variantStyles = {
    info: {
      iconClass: 'text-argus-accent',
      buttonClass: 'bg-argus-accent hover:bg-argus-accent/80',
      Icon: RefreshCcw,
    },
    warning: {
      iconClass: 'text-amber-500',
      buttonClass: 'bg-amber-500 hover:bg-amber-500/80',
      Icon: AlertTriangle,
    },
    danger: {
      iconClass: 'text-argus-loss',
      buttonClass: 'bg-argus-loss hover:bg-argus-loss/80',
      Icon: AlertTriangle,
    },
  };

  const { iconClass, buttonClass, Icon } = variantStyles[variant];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/60 z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: DURATION.fast }}
            onClick={onCancel}
          />

          {/* Modal */}
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="bg-argus-surface border border-argus-border rounded-lg w-full max-w-md shadow-xl"
              initial={{ scale: 0.95, y: 10 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 10 }}
              transition={{ duration: DURATION.normal, ease: EASE.out }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-argus-border">
                <div className={`flex items-center gap-2 ${iconClass}`}>
                  <Icon className="w-5 h-5" />
                  <h2 className="text-lg font-semibold">{title}</h2>
                </div>
                <button
                  onClick={onCancel}
                  className="p-1 rounded hover:bg-argus-surface-2 transition-colors"
                >
                  <X className="w-5 h-5 text-argus-text-dim" />
                </button>
              </div>

              {/* Content */}
              <div className="p-4">
                <p className="text-argus-text">{message}</p>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 p-4 border-t border-argus-border">
                <button
                  onClick={onCancel}
                  disabled={isLoading}
                  className="px-4 py-2 text-sm rounded-md border border-argus-border bg-argus-surface hover:bg-argus-surface-2 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={onConfirm}
                  disabled={isLoading}
                  className={`px-4 py-2 text-sm rounded-md text-white transition-colors disabled:opacity-50 ${buttonClass}`}
                >
                  {isLoading ? 'Processing...' : confirmText}
                </button>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export function GlobalControls() {
  const [rebalanceConfirmOpen, setRebalanceConfirmOpen] = useState(false);
  const [flattenConfirmOpen, setFlattenConfirmOpen] = useState(false);
  const [pauseConfirmOpen, setPauseConfirmOpen] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  const rebalanceMutation = useRebalanceMutation();
  const flattenMutation = useEmergencyFlatten();
  const pauseMutation = useEmergencyPauseAll();

  const handleRebalance = async () => {
    try {
      const result = await rebalanceMutation.mutateAsync();
      setRebalanceConfirmOpen(false);
      setFeedbackMessage({ type: 'success', text: result.message });
      setTimeout(() => setFeedbackMessage(null), 5000);
    } catch (err) {
      setRebalanceConfirmOpen(false);
      setFeedbackMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to rebalance',
      });
      setTimeout(() => setFeedbackMessage(null), 5000);
    }
  };

  const handleFlatten = async () => {
    try {
      const result = await flattenMutation.mutateAsync();
      setFlattenConfirmOpen(false);
      setFeedbackMessage({ type: 'success', text: result.message });
      setTimeout(() => setFeedbackMessage(null), 5000);
    } catch (err) {
      setFlattenConfirmOpen(false);
      setFeedbackMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to flatten positions',
      });
      setTimeout(() => setFeedbackMessage(null), 5000);
    }
  };

  const handlePauseAll = async () => {
    try {
      const result = await pauseMutation.mutateAsync();
      setPauseConfirmOpen(false);
      setFeedbackMessage({ type: 'success', text: result.message });
      setTimeout(() => setFeedbackMessage(null), 5000);
    } catch (err) {
      setPauseConfirmOpen(false);
      setFeedbackMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to pause strategies',
      });
      setTimeout(() => setFeedbackMessage(null), 5000);
    }
  };

  return (
    <>
      <div>
        <CardHeader title="Controls" />
        <Card>
          <div className="space-y-4">
            {/* Feedback message */}
            <AnimatePresence>
              {feedbackMessage && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className={`p-3 rounded-md text-sm ${
                    feedbackMessage.type === 'success'
                      ? 'bg-argus-profit/10 text-argus-profit border border-argus-profit/20'
                      : 'bg-argus-loss/10 text-argus-loss border border-argus-loss/20'
                  }`}
                >
                  {feedbackMessage.text}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Action buttons */}
            <div className="flex flex-col sm:flex-row gap-3">
              {/* Force Rebalance */}
              <button
                onClick={() => setRebalanceConfirmOpen(true)}
                disabled={rebalanceMutation.isPending}
                className="flex items-center justify-center gap-2 flex-1 px-4 py-3 text-sm font-medium rounded-md bg-argus-accent/10 text-argus-accent border border-argus-accent/30 hover:bg-argus-accent/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCcw className="w-4 h-4" />
                Force Rebalance
              </button>

              {/* Emergency Pause All */}
              <button
                onClick={() => setPauseConfirmOpen(true)}
                disabled={pauseMutation.isPending}
                className="flex items-center justify-center gap-2 flex-1 px-4 py-3 text-sm font-medium rounded-md bg-amber-500/10 text-amber-500 border border-amber-500/30 hover:bg-amber-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <PauseCircle className="w-4 h-4" />
                Pause All
              </button>

              {/* Emergency Flatten All */}
              <button
                onClick={() => setFlattenConfirmOpen(true)}
                disabled={flattenMutation.isPending}
                className="flex items-center justify-center gap-2 flex-1 px-4 py-3 text-sm font-medium rounded-md bg-argus-loss/10 text-argus-loss border border-argus-loss/30 hover:bg-argus-loss/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <XCircle className="w-4 h-4" />
                Flatten All
              </button>
            </div>
          </div>
        </Card>
      </div>

      {/* Rebalance confirmation modal */}
      <ConfirmModal
        isOpen={rebalanceConfirmOpen}
        title="Force Rebalance"
        message="Recalculate all strategy allocations based on current account state and performance metrics? This will update capital distribution across strategies."
        confirmText="Rebalance"
        isLoading={rebalanceMutation.isPending}
        variant="info"
        onConfirm={handleRebalance}
        onCancel={() => setRebalanceConfirmOpen(false)}
      />

      {/* Flatten confirmation modal */}
      <ConfirmModal
        isOpen={flattenConfirmOpen}
        title="Emergency Flatten"
        message="This will immediately close ALL open positions at market price. This action cannot be undone. Are you sure?"
        confirmText="Flatten All"
        isLoading={flattenMutation.isPending}
        variant="danger"
        onConfirm={handleFlatten}
        onCancel={() => setFlattenConfirmOpen(false)}
      />

      {/* Pause confirmation modal */}
      <ConfirmModal
        isOpen={pauseConfirmOpen}
        title="Emergency Pause"
        message="This will pause ALL strategies immediately. No new signals will be generated. Existing positions will NOT be closed. Are you sure?"
        confirmText="Pause All"
        isLoading={pauseMutation.isPending}
        variant="warning"
        onConfirm={handlePauseAll}
        onCancel={() => setPauseConfirmOpen(false)}
      />
    </>
  );
}
