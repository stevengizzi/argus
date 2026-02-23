/**
 * Market status and trading mode badge.
 *
 * Shows market open/closed status with color-coded indicator,
 * current time in ET (updates every second), and paper mode badge.
 */

import { useState, useEffect } from 'react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { Badge } from '../../components/Badge';
import { StatusDot } from '../../components/StatusDot';
import { useAccount } from '../../hooks/useAccount';
import { useHealth } from '../../hooks/useHealth';
import { MarketStatusSkeleton } from './DashboardSkeleton';

/** Format current time in ET timezone */
function formatCurrentTimeET(): string {
  return new Date().toLocaleTimeString('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
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

export function MarketStatusBadge() {
  const { data: accountData, isLoading: accountLoading } = useAccount();
  const { data: healthData, isLoading: healthLoading } = useHealth();

  // Local clock that updates every second
  const [currentTime, setCurrentTime] = useState(formatCurrentTimeET);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(formatCurrentTimeET());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  if (accountLoading || healthLoading) {
    return <MarketStatusSkeleton />;
  }

  if (!accountData) {
    return (
      <Card className="h-full">
        <CardHeader title="Market" />
        <div className="text-argus-loss text-sm">Failed to load</div>
      </Card>
    );
  }

  const status = accountData.market_status as MarketStatus;
  const isPaperMode = healthData?.paper_mode ?? true;

  return (
    <Card className="h-full">
      <CardHeader title="Market" />

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

      {/* Current time in ET (updates every second) */}
      <div className="mt-2 text-sm text-argus-text-dim tabular-nums">
        {currentTime} ET
      </div>

      {/* Paper mode badge */}
      {isPaperMode && (
        <div className="mt-3">
          <Badge variant="warning">PAPER</Badge>
        </div>
      )}
    </Card>
  );
}
