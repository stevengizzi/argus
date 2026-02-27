/**
 * Regime Panel - session phase and regime classification display.
 *
 * Full-width card with two zones:
 * - Left/top: Session phase badge, regime badge, next check countdown, last updated
 * - Right/bottom: RegimeInputBreakdown component
 *
 * Desktop: flex-row justify-between. Mobile: stacked.
 */

import { useMemo } from 'react';
import { Card } from '../../components/Card';
import { RegimeBadge } from '../../components/Badge';
import { RegimeInputBreakdown } from './RegimeInputBreakdown';
import type { OrchestratorStatusResponse } from '../../api/types';

interface RegimePanelProps {
  orchestratorData: OrchestratorStatusResponse | null | undefined;
}

// Session phase colors and labels
const SESSION_PHASE_CONFIG: Record<string, { label: string; className: string }> = {
  pre_market: {
    label: 'Pre-Market',
    className: 'text-argus-accent bg-argus-accent/15',
  },
  market_open: {
    label: 'Market Open',
    className: 'text-argus-profit bg-argus-profit-dim',
  },
  midday: {
    label: 'Midday',
    className: 'text-argus-warning bg-argus-warning-dim',
  },
  power_hour: {
    label: 'Power Hour',
    className: 'text-orange-400 bg-orange-400/15',
  },
  after_hours: {
    label: 'After Hours',
    className: 'text-argus-text-dim bg-argus-surface-2',
  },
  market_closed: {
    label: 'Market Closed',
    className: 'text-argus-text-dim bg-argus-surface-2',
  },
};

function formatTimeAgo(timestamp: string | null | undefined): string {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  } catch {
    return '';
  }
}

function computeCountdown(nextCheck: string | null | undefined): string | null {
  if (!nextCheck) return null;
  try {
    const next = new Date(nextCheck);
    const now = new Date();
    const diffMs = next.getTime() - now.getTime();
    if (diffMs <= 0) return 'Now';
    const diffMin = Math.ceil(diffMs / 60000);
    if (diffMin >= 60) {
      const hours = Math.floor(diffMin / 60);
      const mins = diffMin % 60;
      return `${hours}h ${mins}m`;
    }
    return `${diffMin}m`;
  } catch {
    return null;
  }
}

export function RegimePanel({ orchestratorData }: RegimePanelProps) {
  const { sessionPhase, regime, countdown, lastUpdated } = useMemo(() => {
    const phase = orchestratorData?.session_phase ?? 'market_closed';
    const reg = orchestratorData?.regime;
    const cd = computeCountdown(orchestratorData?.next_regime_check);
    const updated = formatTimeAgo(orchestratorData?.regime_updated_at);
    return {
      sessionPhase: phase,
      regime: reg,
      countdown: cd,
      lastUpdated: updated,
    };
  }, [orchestratorData]);

  const phaseConfig = SESSION_PHASE_CONFIG[sessionPhase] ?? SESSION_PHASE_CONFIG.market_closed;

  return (
    <Card>
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 lg:gap-6">
        {/* Left side: Session phase, regime, timing */}
        <div className="space-y-3">
          {/* Session phase badge */}
          <div className="flex items-center gap-3 flex-wrap">
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${phaseConfig.className}`}
            >
              {phaseConfig.label}
            </span>

            {/* Regime badge (scaled up) */}
            {regime && (
              <div className="scale-110 origin-left">
                <RegimeBadge regime={regime} />
              </div>
            )}
          </div>

          {/* Timing info */}
          <div className="flex items-center gap-4 text-xs text-argus-text-dim">
            {countdown && (
              <span>
                Next check in <span className="text-argus-text tabular-nums">{countdown}</span>
              </span>
            )}
            {lastUpdated && (
              <span>
                Updated <span className="text-argus-text">{lastUpdated}</span>
              </span>
            )}
          </div>

          {/* Pre-market completion status */}
          {orchestratorData?.pre_market_complete && orchestratorData?.pre_market_completed_at && (
            <div className="text-xs text-argus-profit">
              Pre-market complete at {formatTimeAgo(orchestratorData.pre_market_completed_at)}
            </div>
          )}
        </div>

        {/* Right side: Regime input breakdown */}
        <div className="lg:text-right">
          <RegimeInputBreakdown regimeIndicators={orchestratorData?.regime_indicators ?? {}} />
        </div>
      </div>
    </Card>
  );
}
