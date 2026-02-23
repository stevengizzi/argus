/**
 * Compact system health status card.
 *
 * Shows component status dots with names, and uptime.
 * Uses warning/error border accent if any component is degraded/error.
 */

import { Activity } from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { StatusDot } from '../../components/StatusDot';
import { useHealth } from '../../hooks/useHealth';
import { formatDuration } from '../../utils/format';
import { HealthMiniSkeleton } from './DashboardSkeleton';

type StatusLevel = 'healthy' | 'degraded' | 'error' | 'unknown';

function mapHealthStatus(status: string): StatusLevel {
  const normalized = status.toLowerCase();
  if (normalized === 'healthy' || normalized === 'ok') return 'healthy';
  if (normalized === 'degraded' || normalized === 'warning') return 'degraded';
  if (normalized === 'error' || normalized === 'unhealthy') return 'error';
  return 'unknown';
}

function getOverallStatus(components: Record<string, { status: string }>): StatusLevel {
  const statuses = Object.values(components).map((c) => mapHealthStatus(c.status));
  if (statuses.includes('error')) return 'error';
  if (statuses.includes('degraded')) return 'degraded';
  if (statuses.every((s) => s === 'healthy')) return 'healthy';
  return 'unknown';
}

function getBorderClass(status: StatusLevel): string {
  if (status === 'error') return 'border-argus-loss';
  if (status === 'degraded') return 'border-argus-warning';
  return '';
}

export function HealthMini() {
  const { data, isLoading, error } = useHealth();

  if (isLoading) {
    return <HealthMiniSkeleton />;
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader title="System Status" />
        <div className="text-argus-loss text-sm">Failed to load status</div>
      </Card>
    );
  }

  const components = data.components ?? {};
  const componentEntries = Object.entries(components);
  const overallStatus = getOverallStatus(components);
  const borderClass = getBorderClass(overallStatus);

  return (
    <Card className={borderClass}>
      <CardHeader
        title="System Status"
        action={
          <div className="flex items-center gap-1.5">
            <StatusDot status={overallStatus} pulse={overallStatus === 'healthy'} />
            <span className="text-xs text-argus-text-dim uppercase">
              {overallStatus === 'healthy' ? 'All OK' : overallStatus.toUpperCase()}
            </span>
          </div>
        }
      />

      {/* Component list */}
      <div className="space-y-2">
        {componentEntries.map(([name, info]) => {
          const status = mapHealthStatus(info.status);
          return (
            <div key={name} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <StatusDot status={status} size="sm" />
                <span className="text-argus-text">{name}</span>
              </div>
              <span className="text-argus-text-dim text-xs">{info.status}</span>
            </div>
          );
        })}
      </div>

      {/* Uptime */}
      <div className="mt-4 pt-3 border-t border-argus-border flex items-center justify-between text-sm">
        <div className="flex items-center gap-2 text-argus-text-dim">
          <Activity className="w-4 h-4" />
          <span>Uptime</span>
        </div>
        <span className="tabular-nums text-argus-text">
          {formatDuration(data.uptime_seconds)}
        </span>
      </div>
    </Card>
  );
}
