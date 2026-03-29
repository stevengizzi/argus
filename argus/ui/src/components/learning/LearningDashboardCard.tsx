/**
 * Learning Dashboard Card — compact summary for the Dashboard page.
 *
 * Shows pending recommendation count, last analysis timestamp, and data
 * quality indicator. Links to Performance page Learning tab.
 * Returns null when learning_loop is disabled.
 *
 * Sprint 28, Session 6c.
 */

import { Brain } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../Card';
import { CardHeader } from '../CardHeader';
import { useLearningReport } from '../../hooks/useLearningReport';
import { useConfigProposals } from '../../hooks/useConfigProposals';
import type { DataQualityPreamble } from '../../api/learningApi';

interface LearningDashboardCardProps {
  /** Whether learning loop is enabled in config. When false, card returns null. */
  enabled?: boolean;
}

type DataQualityLevel = 'sufficient' | 'collecting' | 'sparse';

function assessDataQuality(dq: DataQualityPreamble): DataQualityLevel {
  if (dq.effective_sample_size >= 100 && dq.trading_days_count >= 20) {
    return 'sufficient';
  }
  if (dq.effective_sample_size >= 30 || dq.trading_days_count >= 5) {
    return 'collecting';
  }
  return 'sparse';
}

const QUALITY_DISPLAY: Record<DataQualityLevel, { label: string; color: string }> = {
  sufficient: { label: 'Sufficient', color: 'text-emerald-400' },
  collecting: { label: 'Collecting', color: 'text-amber-400' },
  sparse: { label: 'Sparse', color: 'text-red-400' },
};

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));

  if (diffHrs < 1) return 'Just now';
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  if (diffDays === 1) return 'Yesterday';
  return `${diffDays}d ago`;
}

export function LearningDashboardCard({ enabled = true }: LearningDashboardCardProps) {
  const navigate = useNavigate();
  const { report, isLoading } = useLearningReport(enabled);
  const { data: proposalsData } = useConfigProposals('PENDING', enabled);

  // Hidden when disabled
  if (!enabled) {
    return null;
  }

  const pendingCount = proposalsData?.proposals?.length ?? 0;
  const quality = report?.data_quality
    ? assessDataQuality(report.data_quality)
    : null;
  const qualityDisplay = quality ? QUALITY_DISPLAY[quality] : null;

  const handleNavigate = () => {
    navigate('/performance?tab=learning');
  };

  return (
    <div data-testid="learning-dashboard-card">
    <Card className="h-full">
      <CardHeader
        title="Learning Loop"
        icon={<Brain className="w-4 h-4 text-argus-text-dim" />}
        badge={
          pendingCount > 0 ? (
            <span
              className="text-[10px] font-medium bg-argus-accent/20 text-argus-accent
                border border-argus-accent/30 px-1.5 py-0.5 rounded-full tabular-nums"
              data-testid="pending-count-badge"
            >
              {pendingCount}
            </span>
          ) : undefined
        }
      />

      {/* Loading skeleton */}
      {isLoading && (
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-argus-surface-2 rounded w-20" />
          <div className="h-3 bg-argus-surface-2 rounded w-28" />
        </div>
      )}

      {/* No report yet */}
      {!isLoading && !report && (
        <div className="text-xs text-argus-text-dim">
          No analysis run yet
        </div>
      )}

      {/* Main content */}
      {!isLoading && report && (
        <div className="space-y-2">
          {/* Pending recommendations */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-argus-text-dim">Pending</span>
            <span className="text-sm font-medium text-argus-text tabular-nums">
              {pendingCount} recommendation{pendingCount !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Last analysis */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-argus-text-dim">Last Analysis</span>
            <span className="text-xs text-argus-text tabular-nums">
              {formatTimestamp(report.generated_at)}
            </span>
          </div>

          {/* Data quality */}
          {qualityDisplay && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-argus-text-dim">Data Quality</span>
              <span className={`text-xs font-medium ${qualityDisplay.color}`}>
                {qualityDisplay.label}
              </span>
            </div>
          )}
        </div>
      )}

      {/* View Insights link */}
      <button
        onClick={handleNavigate}
        className="mt-3 text-xs text-argus-accent hover:text-argus-accent/80 transition-colors"
        data-testid="view-insights-link"
      >
        View Insights &rarr;
      </button>
    </Card>
    </div>
  );
}
