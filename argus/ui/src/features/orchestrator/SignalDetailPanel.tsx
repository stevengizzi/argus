/**
 * Expandable detail panel for a quality-scored signal.
 *
 * Shown inline below a signal row in RecentSignals when clicked.
 * Displays quality grade (large badge), score, component breakdown,
 * risk tier, and outcome data if available.
 *
 * Sprint 24.1 Session 4b.
 */

import { QualityBadge } from '../../components/QualityBadge';
import type { QualityScoreResponse } from '../../api/types';
import { getStrategyDisplay } from '../../utils/strategyConfig';

interface SignalDetailPanelProps {
  signal: QualityScoreResponse;
}

export function SignalDetailPanel({ signal }: SignalDetailPanelProps) {
  const strategyDisplay = getStrategyDisplay(signal.strategy_id);

  return (
    <div
      className="px-3 py-3 bg-argus-surface-2/50 border-t border-argus-border"
      data-testid="signal-detail-panel"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Left column: grade badge + score + risk tier */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <QualityBadge
              grade={signal.grade}
              score={signal.score}
              riskTier={signal.risk_tier}
              components={signal.components}
              compact={false}
            />
          </div>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-argus-text-dim">Strategy</span>
              <span className="text-argus-text">{strategyDisplay.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-argus-text-dim">Risk Tier</span>
              <span className="text-argus-text capitalize">{signal.risk_tier}</span>
            </div>
          </div>
        </div>

        {/* Right column: outcome data if available */}
        <div className="space-y-1 text-xs">
          <p className="text-argus-text-dim uppercase tracking-wider font-medium mb-2">
            Outcome
          </p>
          <div className="flex justify-between">
            <span className="text-argus-text-dim">Realized P&L</span>
            <span className="text-argus-text tabular-nums">
              {signal.outcome_realized_pnl !== null
                ? `$${signal.outcome_realized_pnl.toFixed(2)}`
                : '—'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-argus-text-dim">R-Multiple</span>
            <span className="text-argus-text tabular-nums">
              {signal.outcome_r_multiple !== null
                ? `${signal.outcome_r_multiple.toFixed(2)}R`
                : '—'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
