/**
 * Component health status list.
 *
 * Shows all system components with status dots, sorted by severity
 * (errors first, then degraded, then healthy).
 */

import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { StatusDot } from '../../components/StatusDot';
import { useHealth } from '../../hooks/useHealth';
import { ComponentStatusListSkeleton } from './SystemSkeleton';
import type { ComponentStatus as ComponentStatusType } from '../../api/types';

type StatusLevel = 'healthy' | 'degraded' | 'error' | 'unknown';

function mapHealthStatus(status: string): StatusLevel {
  const normalized = status.toLowerCase();
  if (normalized === 'healthy' || normalized === 'ok') return 'healthy';
  if (normalized === 'degraded' || normalized === 'warning') return 'degraded';
  if (normalized === 'error' || normalized === 'unhealthy') return 'error';
  return 'unknown';
}

function getStatusPriority(status: StatusLevel): number {
  switch (status) {
    case 'error':
      return 0;
    case 'degraded':
      return 1;
    case 'unknown':
      return 2;
    case 'healthy':
      return 3;
    default:
      return 4;
  }
}

interface ComponentEntry {
  name: string;
  status: StatusLevel;
  statusText: string;
  details: string;
}

function sortComponents(components: Record<string, ComponentStatusType>): ComponentEntry[] {
  return Object.entries(components)
    .map(([name, info]) => ({
      name,
      status: mapHealthStatus(info.status),
      statusText: info.status,
      details: info.details,
    }))
    .sort((a, b) => getStatusPriority(a.status) - getStatusPriority(b.status));
}

export function ComponentStatusList() {
  const { data, isLoading, error } = useHealth();

  if (isLoading) {
    return <ComponentStatusListSkeleton />;
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader title="Components" />
        <div className="text-argus-loss text-sm">Failed to load component status</div>
      </Card>
    );
  }

  const components = data.components ?? {};
  const sortedComponents = sortComponents(components);

  if (sortedComponents.length === 0) {
    return (
      <Card>
        <CardHeader title="Components" />
        <div className="text-argus-text-dim text-sm">No components registered</div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Components"
        subtitle={`${sortedComponents.length} registered`}
      />

      <div className="space-y-2">
        {sortedComponents.map((component) => (
          <div
            key={component.name}
            className="flex items-start justify-between py-2 border-b border-argus-border last:border-b-0"
          >
            <div className="flex items-start gap-2.5">
              <StatusDot status={component.status} size="sm" />
              <div className="flex-1 min-w-0">
                <div className="text-sm text-argus-text font-medium">
                  {component.name}
                </div>
                {component.details && (
                  <div className="text-xs text-argus-text-dim mt-0.5 truncate">
                    {component.details}
                  </div>
                )}
              </div>
            </div>
            <span className="text-xs text-argus-text-dim uppercase shrink-0 ml-2">
              {component.statusText}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
