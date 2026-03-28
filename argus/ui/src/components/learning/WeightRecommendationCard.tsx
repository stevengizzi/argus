/**
 * Weight recommendation card for Learning Loop.
 *
 * Displays a single weight dimension recommendation with:
 * - Current → recommended weight (delta arrow)
 * - Correlation values, p-value, sample size
 * - Confidence badge (color-coded)
 * - Source divergence warning
 * - Approve/dismiss actions with optional notes
 * - State-specific displays (approved, dismissed, superseded)
 *
 * Sprint 28, Session 6a.
 */

import { useState } from 'react';
import type { WeightRecommendation, ProposalStatus } from '../../api/learningApi';
import { ConfidenceBadge } from './ConfidenceBadge';

interface WeightRecommendationCardProps {
  recommendation: WeightRecommendation;
  proposalId: string;
  status: ProposalStatus;
  humanNotes: string | null;
  onApprove: (proposalId: string, notes?: string) => void;
  onDismiss: (proposalId: string, notes?: string) => void;
  onRevert?: (proposalId: string, notes?: string) => void;
}

export function WeightRecommendationCard({
  recommendation,
  proposalId,
  status,
  humanNotes,
  onApprove,
  onDismiss,
  onRevert,
}: WeightRecommendationCardProps) {
  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState('');
  const [pendingAction, setPendingAction] = useState<'approve' | 'dismiss' | null>(null);

  const isPending = status === 'PENDING';
  const isApproved = status === 'APPROVED' || status === 'APPLIED';
  const isDismissed = status === 'DISMISSED';
  const isSuperseded = status === 'SUPERSEDED';

  const handleAction = (action: 'approve' | 'dismiss') => {
    if (showNotes && pendingAction === action) {
      const handler = action === 'approve' ? onApprove : onDismiss;
      handler(proposalId, notes || undefined);
      setShowNotes(false);
      setNotes('');
      setPendingAction(null);
    } else {
      setShowNotes(true);
      setPendingAction(action);
    }
  };

  const handleRevert = () => {
    onRevert?.(proposalId);
  };

  const deltaSign = recommendation.delta > 0 ? '+' : '';
  const deltaColor =
    recommendation.delta > 0
      ? 'text-argus-profit'
      : recommendation.delta < 0
        ? 'text-argus-loss'
        : 'text-argus-text-dim';

  return (
    <div
      className={`bg-argus-surface border border-argus-border rounded-lg p-4 ${
        isDismissed ? 'opacity-50' : ''
      } ${isSuperseded ? 'opacity-60' : ''}`}
      data-testid="weight-recommendation-card"
    >
      {/* Header: dimension name + confidence badge */}
      <div className="flex items-center justify-between mb-3">
        <h4
          className={`text-sm font-medium text-argus-text ${
            isSuperseded ? 'line-through' : ''
          }`}
        >
          {recommendation.dimension}
        </h4>
        <ConfidenceBadge confidence={recommendation.confidence} />
      </div>

      {/* Superseded label */}
      {isSuperseded && (
        <div
          className="text-xs text-argus-warning mb-2"
          data-testid="superseded-label"
        >
          Superseded by newer report
        </div>
      )}

      {/* Weight change: current → recommended */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm tabular-nums text-argus-text-dim">
          {recommendation.current_weight.toFixed(2)}
        </span>
        <span className="text-argus-text-dim">&rarr;</span>
        <span className="text-sm tabular-nums font-medium text-argus-text">
          {recommendation.recommended_weight.toFixed(2)}
        </span>
        <span className={`text-xs tabular-nums font-medium ${deltaColor}`}>
          ({deltaSign}{recommendation.delta.toFixed(2)})
        </span>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mb-3">
        {recommendation.correlation_trade_source !== null && (
          <>
            <span className="text-argus-text-dim">Trade corr.</span>
            <span className="tabular-nums text-argus-text">
              {recommendation.correlation_trade_source.toFixed(3)}
            </span>
          </>
        )}
        {recommendation.correlation_counterfactual_source !== null && (
          <>
            <span className="text-argus-text-dim">CF corr.</span>
            <span className="tabular-nums text-argus-text">
              {recommendation.correlation_counterfactual_source.toFixed(3)}
            </span>
          </>
        )}
        {recommendation.p_value !== null && (
          <>
            <span className="text-argus-text-dim">p-value</span>
            <span className="tabular-nums text-argus-text">
              {recommendation.p_value.toFixed(4)}
            </span>
          </>
        )}
        <span className="text-argus-text-dim">Sample size</span>
        <span className="tabular-nums text-argus-text">
          {recommendation.sample_size}
        </span>
      </div>

      {/* Source divergence warning */}
      {recommendation.source_divergence_flag && (
        <div
          className="text-xs text-argus-warning bg-argus-warning-dim rounded px-2 py-1 mb-3"
          data-testid="divergence-warning"
        >
          Trade and counterfactual sources diverge
        </div>
      )}

      {/* Approved state */}
      {isApproved && (
        <div className="flex items-center gap-2 mb-2" data-testid="approved-state">
          <span className="text-argus-profit text-sm">&#10003; Approved</span>
          {onRevert && (status === 'APPLIED') && (
            <button
              className="text-xs text-argus-text-dim hover:text-argus-warning transition-colors"
              onClick={handleRevert}
              data-testid="revert-button"
            >
              Revert
            </button>
          )}
        </div>
      )}

      {/* Dismissed state */}
      {isDismissed && (
        <div className="text-sm text-argus-text-dim mb-2" data-testid="dismissed-state">
          Dismissed
        </div>
      )}

      {/* Human notes display */}
      {humanNotes && (
        <div className="text-xs text-argus-text-dim bg-argus-surface-2 rounded px-2 py-1 mb-2">
          {humanNotes}
        </div>
      )}

      {/* Notes textarea (expands on click) */}
      {showNotes && isPending && (
        <div className="mb-2">
          <textarea
            className="w-full bg-argus-surface-2 border border-argus-border rounded text-xs text-argus-text p-2 resize-none"
            placeholder="Optional notes..."
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            data-testid="notes-input"
          />
        </div>
      )}

      {/* Action buttons */}
      {isPending && (
        <div className="flex gap-2">
          <button
            className={`text-xs px-3 py-1 rounded transition-colors ${
              pendingAction === 'approve'
                ? 'bg-argus-profit text-white'
                : 'bg-argus-profit/15 text-argus-profit hover:bg-argus-profit/25'
            }`}
            onClick={() => handleAction('approve')}
            data-testid="approve-button"
          >
            {pendingAction === 'approve' ? 'Confirm Approve' : 'Approve'}
          </button>
          <button
            className={`text-xs px-3 py-1 rounded transition-colors ${
              pendingAction === 'dismiss'
                ? 'bg-argus-loss text-white'
                : 'bg-argus-surface-2 text-argus-text-dim hover:text-argus-text'
            }`}
            onClick={() => handleAction('dismiss')}
            data-testid="dismiss-button"
          >
            {pendingAction === 'dismiss' ? 'Confirm Dismiss' : 'Dismiss'}
          </button>
        </div>
      )}
    </div>
  );
}
