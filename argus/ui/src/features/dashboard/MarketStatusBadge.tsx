/**
 * Market status and trading mode badge.
 *
 * Shows market open/closed status with color-coded indicator,
 * current time in ET, and paper mode badge.
 */

import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { Badge } from '../../components/Badge';
import { StatusDot } from '../../components/StatusDot';
import { LoadingState } from '../../components/LoadingState';
import { useAccount } from '../../hooks/useAccount';
import { useHealth } from '../../hooks/useHealth';
import { formatTime } from '../../utils/format';

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

  if (accountLoading || healthLoading) {
    return (
      <Card className="h-full">
        <CardHeader title="Market" />
        <LoadingState message="Loading..." />
      </Card>
    );
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

      {/* Current time in ET */}
      <div className="mt-2 text-sm text-argus-text-dim tabular-nums">
        {formatTime(accountData.timestamp)} ET
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
