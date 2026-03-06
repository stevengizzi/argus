/**
 * ActionCard component for AI-proposed actions.
 *
 * Renders inline within the chat message list. Shows tool-specific visuals,
 * approval/rejection buttons, countdown timer, and status states.
 *
 * Sprint 22, Session 5.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  Check,
  X,
  Clock,
  Loader2,
  TrendingUp,
  Settings,
  Pause,
  Play,
  FileText,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useCopilotUIStore, type ProposalState } from '../../stores/copilotUI';
import {
  playProposalNotification,
  playExpiryWarning,
  initializeAudioContext,
} from '../../utils/notifications';

interface ActionCardProps {
  proposal: ProposalState;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string, reason?: string) => Promise<void>;
}

// Tool type to visual config mapping
const TOOL_CONFIG: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  propose_allocation_change: {
    icon: <TrendingUp className="w-4 h-4" />,
    label: 'Allocation Change',
    color: 'text-blue-400',
  },
  propose_risk_param_change: {
    icon: <Settings className="w-4 h-4" />,
    label: 'Risk Parameter',
    color: 'text-amber-400',
  },
  propose_strategy_suspend: {
    icon: <Pause className="w-4 h-4" />,
    label: 'Suspend Strategy',
    color: 'text-red-400',
  },
  propose_strategy_resume: {
    icon: <Play className="w-4 h-4" />,
    label: 'Resume Strategy',
    color: 'text-green-400',
  },
  generate_report: {
    icon: <FileText className="w-4 h-4" />,
    label: 'Report',
    color: 'text-purple-400',
  },
};

/**
 * Format seconds remaining as MM:SS.
 */
function formatCountdown(seconds: number): string {
  if (seconds <= 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Get border color class based on status.
 */
function getBorderClass(status: string): string {
  switch (status) {
    case 'pending':
      return 'border-amber-500/50';
    case 'approved':
    case 'executed':
      return 'border-green-500/50';
    case 'rejected':
    case 'expired':
      return 'border-argus-border';
    case 'failed':
      return 'border-red-500/50';
    default:
      return 'border-argus-border';
  }
}

/**
 * Get badge for status.
 */
function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'approved':
      return (
        <span className="flex items-center gap-1 text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded-full">
          <Check className="w-3 h-3" />
          Approved
        </span>
      );
    case 'executed':
      return (
        <span className="flex items-center gap-1 text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded-full">
          <Check className="w-3 h-3" />
          Executed
        </span>
      );
    case 'rejected':
      return (
        <span className="flex items-center gap-1 text-xs text-gray-400 bg-gray-400/10 px-2 py-0.5 rounded-full">
          <X className="w-3 h-3" />
          Rejected
        </span>
      );
    case 'expired':
      return (
        <span className="flex items-center gap-1 text-xs text-gray-400 bg-gray-400/10 px-2 py-0.5 rounded-full">
          <Clock className="w-3 h-3" />
          Expired
        </span>
      );
    case 'failed':
      return (
        <span className="flex items-center gap-1 text-xs text-red-400 bg-red-400/10 px-2 py-0.5 rounded-full">
          <AlertTriangle className="w-3 h-3" />
          Failed
        </span>
      );
    default:
      return null;
  }
}

/**
 * Build a description string based on tool type and input.
 */
function buildDescription(toolName: string, toolInput: Record<string, unknown>): string {
  switch (toolName) {
    case 'propose_allocation_change': {
      const strategy = toolInput.strategy_id as string || 'Unknown';
      const newAlloc = toolInput.new_allocation_pct as number;
      return `${strategy}: → ${newAlloc}%`;
    }
    case 'propose_risk_param_change': {
      const param = toolInput.param_path as string || 'Unknown';
      const oldVal = toolInput.old_value as number;
      const newVal = toolInput.new_value as number;
      return `${param}: ${oldVal} → ${newVal}`;
    }
    case 'propose_strategy_suspend': {
      const strategy = toolInput.strategy_id as string || 'Unknown';
      return `Suspend ${strategy}`;
    }
    case 'propose_strategy_resume': {
      const strategy = toolInput.strategy_id as string || 'Unknown';
      return `Resume ${strategy}`;
    }
    case 'generate_report': {
      const reportType = toolInput.report_type as string || 'report';
      return `Generate ${reportType.replace(/_/g, ' ')}`;
    }
    default:
      return toolName;
  }
}

/**
 * Build a short action description for the confirmation dialog.
 */
function buildActionDescription(toolName: string, toolInput: Record<string, unknown>): string {
  switch (toolName) {
    case 'propose_allocation_change': {
      const strategy = toolInput.strategy_id as string || 'Unknown';
      const newAlloc = toolInput.new_allocation_pct as number;
      return `change ${strategy} allocation to ${newAlloc}%`;
    }
    case 'propose_risk_param_change': {
      const param = toolInput.param_path as string || 'Unknown';
      const newVal = toolInput.new_value as number;
      return `set ${param} to ${newVal}`;
    }
    case 'propose_strategy_suspend': {
      const strategy = toolInput.strategy_id as string || 'Unknown';
      return `suspend ${strategy}`;
    }
    case 'propose_strategy_resume': {
      const strategy = toolInput.strategy_id as string || 'Unknown';
      return `resume ${strategy}`;
    }
    default:
      return 'execute this action';
  }
}

/**
 * Confirmation dialog for approve action.
 */
function ConfirmDialog({
  isOpen,
  description,
  onConfirm,
  onCancel,
  isLoading,
}: {
  isOpen: boolean;
  description: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading: boolean;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-argus-surface border border-argus-border rounded-lg p-4 max-w-sm mx-4 shadow-xl"
      >
        <h3 className="text-base font-medium text-argus-text mb-2">Confirm Action</h3>
        <p className="text-sm text-argus-text-dim mb-4">
          Execute <span className="text-argus-text">{description}</span>? This will take effect immediately.
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="px-3 py-1.5 text-sm text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2 rounded transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="px-3 py-1.5 text-sm bg-green-600 hover:bg-green-500 text-white rounded transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {isLoading && <Loader2 className="w-3 h-3 animate-spin" />}
            Confirm
          </button>
        </div>
      </motion.div>
    </div>
  );
}

/**
 * Reject dialog with optional reason input.
 */
function RejectDialog({
  isOpen,
  onConfirm,
  onCancel,
  isLoading,
}: {
  isOpen: boolean;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
  isLoading: boolean;
}) {
  const [reason, setReason] = useState('');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-argus-surface border border-argus-border rounded-lg p-4 max-w-sm mx-4 shadow-xl"
      >
        <h3 className="text-base font-medium text-argus-text mb-2">Reject Action</h3>
        <p className="text-sm text-argus-text-dim mb-3">
          Optionally provide a reason for rejection:
        </p>
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason (optional)"
          className="w-full px-3 py-2 text-sm bg-argus-bg border border-argus-border rounded mb-4 text-argus-text placeholder:text-argus-text-dim focus:outline-none focus:border-argus-accent"
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="px-3 py-1.5 text-sm text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2 rounded transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(reason)}
            disabled={isLoading}
            className="px-3 py-1.5 text-sm bg-red-600 hover:bg-red-500 text-white rounded transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {isLoading && <Loader2 className="w-3 h-3 animate-spin" />}
            Reject
          </button>
        </div>
      </motion.div>
    </div>
  );
}

/**
 * Main ActionCard component.
 */
export function ActionCard({ proposal, onApprove, onReject }: ActionCardProps) {
  const { updateProposal, notificationsEnabled } = useCopilotUIStore();
  const [secondsRemaining, setSecondsRemaining] = useState<number>(0);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const hasPlayedNotificationRef = useRef(false);
  const hasPlayedExpiryWarningRef = useRef(proposal.expiryWarningPlayed ?? false);

  const config = TOOL_CONFIG[proposal.toolName] || {
    icon: <Settings className="w-4 h-4" />,
    label: proposal.toolName,
    color: 'text-argus-text-dim',
  };

  // Initialize audio context on first interaction
  useEffect(() => {
    const handleInteraction = () => {
      initializeAudioContext();
      document.removeEventListener('click', handleInteraction);
      document.removeEventListener('keydown', handleInteraction);
    };
    document.addEventListener('click', handleInteraction);
    document.addEventListener('keydown', handleInteraction);
    return () => {
      document.removeEventListener('click', handleInteraction);
      document.removeEventListener('keydown', handleInteraction);
    };
  }, []);

  // Play notification on mount for new pending proposals
  useEffect(() => {
    if (
      proposal.status === 'pending' &&
      notificationsEnabled &&
      !hasPlayedNotificationRef.current
    ) {
      playProposalNotification();
      hasPlayedNotificationRef.current = true;
    }
  }, [proposal.status, notificationsEnabled]);

  // Countdown timer
  useEffect(() => {
    if (proposal.status !== 'pending') return;

    const updateCountdown = () => {
      const expiresAt = new Date(proposal.expiresAt).getTime();
      const now = Date.now();
      const remaining = Math.max(0, Math.floor((expiresAt - now) / 1000));
      setSecondsRemaining(remaining);

      // Play expiry warning when < 60 seconds (once)
      if (
        remaining > 0 &&
        remaining < 60 &&
        notificationsEnabled &&
        !hasPlayedExpiryWarningRef.current
      ) {
        playExpiryWarning();
        hasPlayedExpiryWarningRef.current = true;
        // Persist this to the store so it's remembered across re-renders
        updateProposal(proposal.id, { expiryWarningPlayed: true });
      }

      // Client-side expiry
      if (remaining <= 0) {
        updateProposal(proposal.id, { status: 'expired' });
      }
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [proposal.id, proposal.status, proposal.expiresAt, notificationsEnabled, updateProposal]);

  const handleApproveClick = useCallback(() => {
    setShowConfirmDialog(true);
  }, []);

  const handleConfirmApprove = useCallback(async () => {
    setIsApproving(true);
    try {
      await onApprove(proposal.id);
      setShowConfirmDialog(false);
    } finally {
      setIsApproving(false);
    }
  }, [proposal.id, onApprove]);

  const handleRejectClick = useCallback(() => {
    setShowRejectDialog(true);
  }, []);

  const handleConfirmReject = useCallback(async (reason: string) => {
    setIsRejecting(true);
    try {
      await onReject(proposal.id, reason);
      setShowRejectDialog(false);
    } finally {
      setIsRejecting(false);
    }
  }, [proposal.id, onReject]);

  // Keyboard shortcuts for approve/reject
  useEffect(() => {
    if (proposal.status !== 'pending') return;
    if (proposal.toolName === 'generate_report') return; // Reports auto-execute

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT') return;

      if (e.key === 'y' || (e.key === 'Enter' && !showConfirmDialog && !showRejectDialog)) {
        e.preventDefault();
        handleApproveClick();
      } else if (e.key === 'n') {
        e.preventDefault();
        handleRejectClick();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [proposal.status, proposal.toolName, showConfirmDialog, showRejectDialog, handleApproveClick, handleRejectClick]);

  const isDimmed = proposal.status === 'rejected' || proposal.status === 'expired';
  const isUrgent = proposal.status === 'pending' && secondsRemaining < 60 && secondsRemaining > 0;
  const description = buildDescription(proposal.toolName, proposal.toolInput);
  const reason = proposal.toolInput.reason as string | undefined;

  return (
    <>
      <div
        className={`rounded-lg border p-3 ${getBorderClass(proposal.status)} ${
          isDimmed ? 'opacity-60' : ''
        } bg-argus-surface-2`}
        data-testid="action-card"
        data-status={proposal.status}
      >
        {/* Header row */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <span className={config.color}>{config.icon}</span>
            <span className="text-sm font-medium text-argus-text">{config.label}</span>
          </div>
          <div className="flex items-center gap-2">
            {/* Status badge or countdown */}
            {proposal.status === 'pending' ? (
              <span
                className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                  isUrgent
                    ? 'text-red-400 bg-red-400/10 animate-pulse'
                    : 'text-amber-400 bg-amber-400/10'
                }`}
              >
                <Clock className="w-3 h-3" />
                {formatCountdown(secondsRemaining)}
              </span>
            ) : (
              <StatusBadge status={proposal.status} />
            )}
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-argus-text mb-1">{description}</p>
        {reason && (
          <p className="text-xs text-argus-text-dim mb-2">{reason}</p>
        )}

        {/* Status-specific content */}
        {proposal.status === 'approved' && (
          <div className="flex items-center gap-2 text-sm text-green-400 mt-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Executing...</span>
          </div>
        )}

        {proposal.status === 'executed' && proposal.result && (
          <>
            {/* Report click-through for generate_report */}
            {proposal.toolName === 'generate_report' && proposal.result.content ? (
              <div className="mt-2">
                <button
                  type="button"
                  onClick={() => setShowReport(!showReport)}
                  className="flex items-center gap-1.5 text-sm text-purple-400 hover:text-purple-300 transition-colors"
                >
                  {showReport ? (
                    <>
                      <ChevronUp className="w-4 h-4" />
                      Hide Report
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-4 h-4" />
                      View Report
                    </>
                  )}
                </button>
                {showReport && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-2 p-3 bg-argus-bg rounded-lg border border-argus-border text-xs text-argus-text whitespace-pre-wrap max-h-64 overflow-y-auto"
                  >
                    {proposal.result.content as string}
                  </motion.div>
                )}
              </div>
            ) : (
              <div className="text-xs text-green-400 mt-2 bg-green-400/10 rounded px-2 py-1">
                {proposal.result.message as string || 'Action completed successfully'}
              </div>
            )}
          </>
        )}

        {proposal.status === 'failed' && proposal.failureReason && (
          <div className="text-xs text-red-400 mt-2 bg-red-400/10 rounded px-2 py-1">
            {proposal.failureReason}
          </div>
        )}

        {/* Action buttons for pending state */}
        {proposal.status === 'pending' && proposal.toolName !== 'generate_report' && (
          <>
            <div className="flex items-center gap-2 mt-3">
              <button
                type="button"
                onClick={handleApproveClick}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm bg-green-600 hover:bg-green-500 text-white rounded transition-colors"
              >
                <Check className="w-3.5 h-3.5" />
                Approve
              </button>
              <button
                type="button"
                onClick={handleRejectClick}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm bg-red-600 hover:bg-red-500 text-white rounded transition-colors"
              >
                <X className="w-3.5 h-3.5" />
                Reject
              </button>
            </div>
            <p className="text-xs text-argus-text-dim text-center mt-1.5">
              Y to approve · N to reject
            </p>
          </>
        )}
      </div>

      {/* Dialogs */}
      <ConfirmDialog
        isOpen={showConfirmDialog}
        description={buildActionDescription(proposal.toolName, proposal.toolInput)}
        onConfirm={handleConfirmApprove}
        onCancel={() => setShowConfirmDialog(false)}
        isLoading={isApproving}
      />
      <RejectDialog
        isOpen={showRejectDialog}
        onConfirm={handleConfirmReject}
        onCancel={() => setShowRejectDialog(false)}
        isLoading={isRejecting}
      />
    </>
  );
}
