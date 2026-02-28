/**
 * Combined Market Status Card showing market state and regime.
 *
 * Sprint 21d Code Review Fix #4: Merge Market + Market Regime into one card.
 * - Top section: Market status with dot indicator, time, PAPER badge
 * - Bottom section: Regime badge with description and last updated
 */

import { useState, useEffect } from 'react';
import { Card } from '../../components/Card';
import { Badge, RegimeBadge } from '../../components/Badge';
import { StatusDot } from '../../components/StatusDot';
import { useAccount } from '../../hooks/useAccount';
import { useHealth } from '../../hooks/useHealth';
import { useOrchestratorStatus } from '../../hooks';

/** Format current time in ET timezone */
function formatCurrentTimeET(): string {
  return new Date().toLocaleTimeString('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: '2-digit',
  });
}

type MarketStatus = 'pre_market' | 'open' | 'closed' | 'after_hours';

const statusLabels: Record<MarketStatus, string> = {
  pre_market: 'PRE-MKT',
  open: 'OPEN',
  closed: 'CLOSED',
  after_hours: 'AFTER-HRS',
};

const statusColors: Record<MarketStatus, 'healthy' | 'degraded' | 'unknown'> = {
  pre_market: 'degraded',
  open: 'healthy',
  closed: 'unknown',
  after_hours: 'degraded',
};

// Regime descriptions
const REGIME_DESCRIPTIONS: Record<string, string> = {
  bullish: 'Strong upward momentum',
  bullish_trending: 'Strong upward momentum',
  bearish: 'Strong downward momentum',
  bearish_trending: 'Strong downward momentum',
  range: 'Consolidating in range',
  range_bound: 'Consolidating in range',
  high_vol: 'Elevated volatility',
  crisis: 'Extreme conditions',
};

export function MarketStatusCard() {
  const { data: accountData, isLoading: accountLoading } = useAccount();
  const { data: healthData, isLoading: healthLoading } = useHealth();
  const { data: orchestratorData, isLoading: orchestratorLoading } = useOrchestratorStatus();

  // Local clock that updates every second
  const [currentTime, setCurrentTime] = useState(formatCurrentTimeET);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(formatCurrentTimeET());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Loading state
  if (accountLoading || healthLoading || orchestratorLoading) {
    return (
      <Card className="h-full">
        <div className="animate-pulse space-y-3">
          <div className="h-3 w-20 bg-argus-surface-2 rounded" />
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 bg-argus-surface-2 rounded-full" />
            <div className="h-5 w-16 bg-argus-surface-2 rounded" />
          </div>
          <div className="h-4 w-24 bg-argus-surface-2 rounded" />
          <div className="border-t border-argus-border/50 pt-3 mt-3">
            <div className="h-5 w-20 bg-argus-surface-2 rounded-full mx-auto" />
          </div>
        </div>
      </Card>
    );
  }

  const status = (accountData?.market_status as MarketStatus) ?? 'closed';
  const isPaperMode = healthData?.paper_mode ?? true;

  const regime = orchestratorData?.regime;
  const normalizedRegime = regime?.toLowerCase().replace(/[-\s]/g, '_');
  const regimeDescription = normalizedRegime ? REGIME_DESCRIPTIONS[normalizedRegime] : null;

  return (
    <Card className="h-full flex flex-col">
      {/* Header */}
      <h3 className="text-xs font-medium uppercase tracking-wider text-argus-text-dim mb-2">
        Market Status
      </h3>

      {/* Market status with dot */}
      <div className="flex items-center gap-2">
        <StatusDot
          status={statusColors[status]}
          pulse={status === 'open'}
          size="md"
        />
        <span className="text-lg font-medium text-argus-text">
          {statusLabels[status]}
        </span>
      </div>

      {/* Current time + badges */}
      <div className="flex items-center gap-2 mt-1">
        <span className="text-sm text-argus-text-dim tabular-nums">
          {currentTime} ET
        </span>
        {isPaperMode && (
          <span className="text-[10px]">
            <Badge variant="warning">PAPER</Badge>
          </span>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-argus-border/50 my-3" />

      {/* Regime section */}
      {regime ? (
        <div className="flex items-center gap-2">
          <RegimeBadge regime={regime} />
          {regimeDescription && (
            <span className="text-xs text-argus-text-dim truncate">
              {regimeDescription}
            </span>
          )}
        </div>
      ) : (
        <div className="text-xs text-argus-text-dim">
          Regime data available during market hours
        </div>
      )}

      {/* Last updated */}
      {orchestratorData?.regime_updated_at && (
        <div className="text-[10px] text-argus-text-dim mt-1">
          Updated{' '}
          {new Date(orchestratorData.regime_updated_at).toLocaleTimeString(
            'en-US',
            { hour: 'numeric', minute: '2-digit' }
          )}
        </div>
      )}
    </Card>
  );
}
