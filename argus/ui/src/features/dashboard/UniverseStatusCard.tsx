/**
 * Universe Status Card for the Dashboard.
 *
 * Displays universe monitoring stats from the Universe Manager.
 * Shows viable symbol count, per-strategy matches, and data freshness.
 *
 * Sprint 23: NLP Catalyst + Universe Manager
 */

import { Globe, RefreshCw } from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { useUniverseStatus } from '../../hooks';

/**
 * Format reference data age into human-readable string.
 */
function formatDataAge(minutes: number | null): string {
  if (minutes === null) return 'Unknown';
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${Math.round(minutes)} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/**
 * Skeleton loader for the Universe Status card.
 */
function UniverseStatusSkeleton() {
  return (
    <Card className="h-full">
      <CardHeader title="Universe" />
      <div className="animate-pulse space-y-3">
        <div className="h-8 bg-argus-surface-2 rounded w-24" />
        <div className="space-y-2">
          <div className="h-3 bg-argus-surface-2 rounded w-full" />
          <div className="h-3 bg-argus-surface-2 rounded w-5/6" />
          <div className="h-3 bg-argus-surface-2 rounded w-3/4" />
        </div>
        <div className="h-3 bg-argus-surface-2 rounded w-20" />
      </div>
    </Card>
  );
}

/**
 * Error state for the Universe Status card.
 */
function UniverseStatusError({ onRetry }: { onRetry: () => void }) {
  return (
    <Card className="h-full">
      <CardHeader title="Universe" />
      <div className="text-argus-text-dim text-sm">
        Unable to load universe status
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 text-sm text-argus-accent hover:text-argus-accent-bright hover:underline transition-colors flex items-center gap-1.5 cursor-pointer"
      >
        <RefreshCw className="w-3.5 h-3.5" />
        Retry
      </button>
    </Card>
  );
}

/**
 * Disabled state when Universe Manager is not enabled.
 */
function UniverseStatusDisabled() {
  return (
    <Card className="h-full">
      <CardHeader title="Universe" />
      <div className="flex items-center gap-2 text-argus-text-dim">
        <Globe className="w-4 h-4" />
        <span className="text-sm">Universe Manager not enabled</span>
      </div>
    </Card>
  );
}

export function UniverseStatusCard() {
  const { data, isLoading, error, refetch, isFetching } = useUniverseStatus();

  // Show skeleton while loading
  if (isLoading) {
    return <UniverseStatusSkeleton />;
  }

  // Show error state
  if (error) {
    return <UniverseStatusError onRetry={() => refetch()} />;
  }

  // Check if Universe Manager is disabled
  if (!data || !data.enabled) {
    return <UniverseStatusDisabled />;
  }

  // Enabled state - show universe stats
  const viableCount = data.viable_count ?? 0;
  const strategyCountEntries = data.per_strategy_counts
    ? Object.entries(data.per_strategy_counts)
    : [];
  const dataAge = formatDataAge(data.reference_data_age_minutes);

  return (
    <Card className="h-full">
      <CardHeader title="Universe" />

      {/* Viable count - prominent display */}
      <div className="mb-3">
        <div className="text-3xl font-semibold text-argus-text tabular-nums">
          {viableCount.toLocaleString()}
        </div>
        <div className="text-xs text-argus-text-dim">viable symbols</div>
      </div>

      {/* Per-strategy counts */}
      {strategyCountEntries.length > 0 && (
        <div className="space-y-1.5 mb-3">
          {strategyCountEntries.map(([strategyId, count]) => (
            <div
              key={strategyId}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-argus-text-dim truncate pr-2">
                {strategyId}
              </span>
              <span className="text-argus-text tabular-nums font-medium">
                {count}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Footer with data age and refresh */}
      <div className="flex items-center justify-between text-xs text-argus-text-dim pt-2 border-t border-argus-border">
        <span>Updated {dataAge}</span>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-1 text-argus-accent hover:text-argus-accent-bright hover:underline transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          aria-label="Refresh universe status"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`}
          />
          Refresh
        </button>
      </div>
    </Card>
  );
}
