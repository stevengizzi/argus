/**
 * Component health status list with filter.
 *
 * Shows all system components with status dots, sorted by severity
 * (errors first, then degraded, then healthy).
 *
 * Updated with SegmentedTab for status filter (17-B).
 */

import { useState, useMemo } from 'react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { StatusDot } from '../../components/StatusDot';
import { SegmentedTab } from '../../components/SegmentedTab';
import { useHealth } from '../../hooks/useHealth';
import { ComponentStatusListSkeleton } from './SystemSkeleton';
import type { ComponentStatus as ComponentStatusType } from '../../api/types';
import type { SegmentedTabSegment } from '../../components/SegmentedTab';

type StatusLevel = 'healthy' | 'degraded' | 'error' | 'unknown';
type StatusFilter = 'all' | 'healthy' | 'degraded' | 'down';

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
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const components = data?.components ?? {};
  const sortedComponents = useMemo(() => sortComponents(components), [components]);

  // Compute counts for each status
  const statusCounts = useMemo(() => {
    const counts = { healthy: 0, degraded: 0, down: 0 };
    for (const component of sortedComponents) {
      if (component.status === 'healthy') counts.healthy++;
      else if (component.status === 'degraded') counts.degraded++;
      else counts.down++; // error + unknown = down
    }
    return counts;
  }, [sortedComponents]);

  // Filter components based on selected status
  const filteredComponents = useMemo(() => {
    if (statusFilter === 'all') return sortedComponents;
    if (statusFilter === 'healthy') return sortedComponents.filter(c => c.status === 'healthy');
    if (statusFilter === 'degraded') return sortedComponents.filter(c => c.status === 'degraded');
    if (statusFilter === 'down') return sortedComponents.filter(c => c.status === 'error' || c.status === 'unknown');
    return sortedComponents;
  }, [sortedComponents, statusFilter]);

  // Build filter segments with counts
  const filterSegments: SegmentedTabSegment[] = useMemo(() => [
    {
      label: 'All',
      value: 'all',
      count: sortedComponents.length,
    },
    {
      label: 'Healthy',
      value: 'healthy',
      count: statusCounts.healthy,
      countVariant: 'success' as const,
    },
    {
      label: 'Degraded',
      value: 'degraded',
      count: statusCounts.degraded,
      countVariant: 'warning' as const,
    },
    {
      label: 'Down',
      value: 'down',
      count: statusCounts.down,
      countVariant: 'danger' as const,
    },
  ], [sortedComponents.length, statusCounts]);

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

      {/* Status filter */}
      <div className="mb-4">
        <SegmentedTab
          segments={filterSegments}
          activeValue={statusFilter}
          onChange={(value) => setStatusFilter(value as StatusFilter)}
          size="sm"
          layoutId="component-status-filter"
        />
      </div>

      <div className="space-y-2">
        {filteredComponents.length === 0 ? (
          <div className="text-argus-text-dim text-sm py-4 text-center">
            No components match filter
          </div>
        ) : (
          filteredComponents.map((component) => (
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
          ))
        )}
      </div>
    </Card>
  );
}
