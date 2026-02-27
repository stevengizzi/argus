/**
 * Regime Panel - market regime classification display.
 *
 * Redesigned layout (Sprint 21b):
 * - Regime badge is the hero element (large, prominent)
 * - Session phase moved to page header
 * - Three regime inputs shown as visual gauge bars
 *
 * Desktop: flex-row justify-between. Mobile: stacked.
 */

import { useMemo } from 'react';
import { Card } from '../../components/Card';
import { RegimeBadge } from '../../components/Badge';
import { RegimeGauges } from './RegimeGauges';
import type { OrchestratorStatusResponse } from '../../api/types';

interface RegimePanelProps {
  orchestratorData: OrchestratorStatusResponse | null | undefined;
  className?: string;
}

function formatTimeAgo(timestamp: string | null | undefined): string {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  } catch {
    return '';
  }
}

export function RegimePanel({ orchestratorData, className }: RegimePanelProps) {
  const { regime, lastUpdated, preMarketComplete, preMarketTime } = useMemo(() => {
    const reg = orchestratorData?.regime;
    const updated = formatTimeAgo(orchestratorData?.regime_updated_at);
    const pmComplete = orchestratorData?.pre_market_complete ?? false;
    const pmTime = formatTimeAgo(orchestratorData?.pre_market_completed_at);
    return {
      regime: reg,
      lastUpdated: updated,
      preMarketComplete: pmComplete,
      preMarketTime: pmTime,
    };
  }, [orchestratorData]);

  return (
    <Card className={className}>
      <div className="flex flex-col h-full">
        {/* Top: Large regime badge + timestamps */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            {regime && (
              <div className="scale-125 origin-left">
                <RegimeBadge regime={regime} />
              </div>
            )}
          </div>
          <div className="flex flex-col items-end gap-1 text-xs text-argus-text-dim">
            {lastUpdated && <span>Updated {lastUpdated}</span>}
            {preMarketComplete && preMarketTime && (
              <span className="text-argus-profit">Pre-market complete at {preMarketTime}</span>
            )}
          </div>
        </div>

        {/* Gauges fill remaining space */}
        <div className="flex-1 flex flex-col justify-center">
          <RegimeGauges regimeIndicators={orchestratorData?.regime_indicators ?? {}} />
        </div>
      </div>
    </Card>
  );
}

// Export computeCountdown for use in OrchestratorPage
export function computeCountdown(nextCheck: string | null | undefined): string | null {
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
