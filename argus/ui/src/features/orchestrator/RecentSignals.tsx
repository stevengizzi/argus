/**
 * Recent quality-scored signals panel for Orchestrator page.
 *
 * Displays the last N signals with symbol, strategy, QualityBadge, and
 * timestamp. Auto-refreshes via useQualityHistory polling.
 *
 * Sprint 24 Session 10.
 */

import { Card } from '../../components/Card';
import { QualityBadge } from '../../components/QualityBadge';
import { useQualityHistory } from '../../hooks/useQuality';
import { getStrategyDisplay } from '../../utils/strategyConfig';

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function RecentSignals() {
  const { data, isLoading } = useQualityHistory({ limit: 10 });

  if (isLoading) {
    return (
      <Card>
        <p className="text-xs font-medium text-argus-text-dim uppercase tracking-wider mb-3">
          Recent Signals
        </p>
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-8 bg-argus-surface-2 rounded animate-pulse" />
          ))}
        </div>
      </Card>
    );
  }

  const signals = data?.items ?? [];

  if (signals.length === 0) {
    return (
      <Card>
        <p className="text-xs font-medium text-argus-text-dim uppercase tracking-wider mb-3">
          Recent Signals
        </p>
        <div
          className="flex items-center justify-center h-32"
          data-testid="recent-signals-empty"
        >
          <p className="text-sm text-argus-text-dim">No recent signals</p>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <p className="text-xs font-medium text-argus-text-dim uppercase tracking-wider mb-3">
        Recent Signals
      </p>
      <div className="space-y-1" data-testid="recent-signals-list">
        {signals.map((signal, idx) => {
          const strategyDisplay = signal.strategy_id
            ? getStrategyDisplay(signal.strategy_id)
            : { shortName: 'Unknown', fullName: 'Unknown', color: 'text-gray-400', bgColor: 'bg-gray-400' };
          return (
            <div
              key={`${signal.symbol}-${signal.scored_at}-${idx}`}
              className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-argus-surface-2 transition-colors"
              data-testid="recent-signal-row"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-sm font-medium text-argus-text w-14 shrink-0">
                  {signal.symbol}
                </span>
                <span className="text-xs text-argus-text-dim truncate">
                  {strategyDisplay.shortName}
                </span>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <QualityBadge
                  grade={signal.grade}
                  score={signal.score}
                  riskTier={signal.risk_tier}
                />
                <span className="text-xs text-argus-text-dim tabular-nums w-16 text-right">
                  {formatTime(signal.scored_at)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
