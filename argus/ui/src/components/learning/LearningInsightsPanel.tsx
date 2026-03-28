/**
 * Learning Insights Panel — composes weight + threshold recommendation cards.
 *
 * Features:
 * - Data quality preamble (trading days, sample sizes, known gaps)
 * - "Run Analysis" button (triggers useTriggerAnalysis mutation)
 * - Last analysis timestamp display
 * - Report selector dropdown for historical reports
 * - Per-regime toggle (collapsed by default)
 * - Empty state: no reports yet
 * - Disabled state: learning loop off in config
 *
 * Sprint 28, Session 6b.
 */

import { useState, useMemo } from 'react';
import { Card } from '../Card';
import { WeightRecommendationCard } from './WeightRecommendationCard';
import { ThresholdRecommendationCard } from './ThresholdRecommendationCard';
import { useLearningReport, useLearningReports, useTriggerAnalysis } from '../../hooks/useLearningReport';
import { useConfigProposals, useApproveProposal, useDismissProposal, useRevertProposal } from '../../hooks/useConfigProposals';
import type { LearningReport, ConfigProposal } from '../../api/learningApi';

interface LearningInsightsPanelProps {
  /** Whether the learning loop is enabled in config. */
  enabled?: boolean;
  /** Controls TanStack Query `enabled` — only fetch when tab is active. */
  isActive?: boolean;
}

export function LearningInsightsPanel({
  enabled = true,
  isActive = true,
}: LearningInsightsPanelProps) {
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [showRegimeBreakdown, setShowRegimeBreakdown] = useState(false);

  // Hooks — gated by isActive to prevent fetches when tab is not selected
  const {
    report: latestReport,
    isLoading: reportLoading,
    isError: reportError,
  } = useLearningReport(isActive && enabled);

  const { data: reportsList } = useLearningReports(
    undefined,
    undefined,
    isActive && enabled
  );

  const triggerMutation = useTriggerAnalysis();

  const { data: proposalsData } = useConfigProposals(
    undefined,
    isActive && enabled
  );

  const approveMutation = useApproveProposal();
  const dismissMutation = useDismissProposal();
  const revertMutation = useRevertProposal();

  // Determine which report to display
  const activeReport: LearningReport | null = latestReport;
  const reports = reportsList?.reports ?? [];

  // Build proposal lookup keyed by field_path for matching to recommendations
  const proposalsByField = useMemo(() => {
    const map = new Map<string, ConfigProposal>();
    if (proposalsData?.proposals) {
      for (const proposal of proposalsData.proposals) {
        map.set(proposal.field_path, proposal);
      }
    }
    return map;
  }, [proposalsData]);

  // Action handlers
  const handleApprove = (proposalId: string, notes?: string) => {
    approveMutation.mutate({ proposalId, notes });
  };

  const handleDismiss = (proposalId: string, notes?: string) => {
    dismissMutation.mutate({ proposalId, notes });
  };

  const handleRevert = (proposalId: string, notes?: string) => {
    revertMutation.mutate({ proposalId, notes });
  };

  const handleRunAnalysis = () => {
    triggerMutation.mutate();
  };

  // --- Disabled state ---
  if (!enabled) {
    return (
      <Card>
        <div className="text-center py-12" data-testid="learning-disabled">
          <div className="w-10 h-10 rounded-full bg-argus-surface-2 flex items-center justify-center mx-auto mb-4">
            <span className="text-argus-text-dim text-lg">&#x1F6AB;</span>
          </div>
          <p className="text-argus-text-dim text-sm">
            Learning Loop is disabled in config
          </p>
        </div>
      </Card>
    );
  }

  // --- Loading state ---
  if (reportLoading) {
    return (
      <Card>
        <div className="space-y-4 animate-pulse" data-testid="learning-loading">
          <div className="h-4 bg-argus-surface-2 rounded w-1/3" />
          <div className="h-20 bg-argus-surface-2 rounded" />
          <div className="h-20 bg-argus-surface-2 rounded" />
        </div>
      </Card>
    );
  }

  // --- Error state ---
  if (reportError) {
    return (
      <Card>
        <div className="text-center py-12">
          <p className="text-argus-loss text-sm">Failed to load learning data</p>
          <button
            onClick={handleRunAnalysis}
            className="text-argus-accent hover:underline text-sm mt-4"
          >
            Try running analysis
          </button>
        </div>
      </Card>
    );
  }

  // --- Empty state ---
  if (!activeReport) {
    return (
      <Card>
        <div className="text-center py-12" data-testid="learning-empty">
          <div className="w-10 h-10 rounded-full bg-argus-surface-2 flex items-center justify-center mx-auto mb-4">
            <span className="text-argus-text-dim text-lg">&#x1F4CA;</span>
          </div>
          <p className="text-argus-text-dim text-sm mb-4">
            No analysis reports yet. Run your first analysis after a trading session.
          </p>
          <button
            onClick={handleRunAnalysis}
            disabled={triggerMutation.isPending}
            className="px-4 py-2 bg-argus-accent text-white text-sm rounded hover:bg-argus-accent/80 transition-colors disabled:opacity-50"
            data-testid="run-analysis-button"
          >
            {triggerMutation.isPending ? 'Running...' : 'Run Analysis'}
          </button>
        </div>
      </Card>
    );
  }

  // --- Main content ---
  const { data_quality, weight_recommendations, threshold_recommendations } = activeReport;
  const pendingCount =
    weight_recommendations.length + threshold_recommendations.length;

  return (
    <div className="space-y-4" data-testid="learning-insights-panel">
      {/* Header: Run Analysis + Report Selector */}
      <Card>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium text-argus-text">Learning Analysis</h3>
            <p className="text-xs text-argus-text-dim mt-0.5">
              Last run:{' '}
              {new Date(activeReport.generated_at).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Report selector */}
            {reports.length > 1 && (
              <select
                className="bg-argus-surface-2 border border-argus-border rounded text-xs text-argus-text px-2 py-1.5"
                value={selectedReportId ?? activeReport.report_id}
                onChange={(e) => setSelectedReportId(e.target.value)}
                data-testid="report-selector"
              >
                {reports.map((r) => (
                  <option key={r.report_id} value={r.report_id}>
                    {new Date(r.generated_at).toLocaleDateString()}
                    {' — '}
                    {r.weight_recommendations + r.threshold_recommendations} recs
                  </option>
                ))}
              </select>
            )}
            <button
              onClick={handleRunAnalysis}
              disabled={triggerMutation.isPending}
              className="px-3 py-1.5 bg-argus-accent text-white text-xs rounded hover:bg-argus-accent/80 transition-colors disabled:opacity-50 flex items-center gap-1.5"
              data-testid="run-analysis-button"
            >
              {triggerMutation.isPending && (
                <span className="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              {triggerMutation.isPending ? 'Running...' : 'Run Analysis'}
            </button>
          </div>
        </div>
      </Card>

      {/* Data Quality Preamble */}
      <Card>
        <h4 className="text-xs font-medium text-argus-text-dim uppercase tracking-wide mb-2">
          Data Quality
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <span className="text-argus-text-dim">Trading Days</span>
            <p className="text-argus-text font-medium tabular-nums">{data_quality.trading_days_count}</p>
          </div>
          <div>
            <span className="text-argus-text-dim">Total Trades</span>
            <p className="text-argus-text font-medium tabular-nums">{data_quality.total_trades}</p>
          </div>
          <div>
            <span className="text-argus-text-dim">Counterfactual</span>
            <p className="text-argus-text font-medium tabular-nums">{data_quality.total_counterfactual}</p>
          </div>
          <div>
            <span className="text-argus-text-dim">Effective Sample</span>
            <p className="text-argus-text font-medium tabular-nums">{data_quality.effective_sample_size}</p>
          </div>
        </div>
        {data_quality.known_data_gaps.length > 0 && (
          <div className="mt-2 text-xs text-argus-warning">
            Known gaps: {data_quality.known_data_gaps.join(', ')}
          </div>
        )}
      </Card>

      {/* Per-regime toggle */}
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-2 text-xs text-argus-text-dim cursor-pointer">
          <input
            type="checkbox"
            checked={showRegimeBreakdown}
            onChange={(e) => setShowRegimeBreakdown(e.target.checked)}
            className="rounded border-argus-border"
            data-testid="regime-toggle"
          />
          Show regime-conditional breakdown
        </label>
      </div>

      {/* Weight Recommendations */}
      {weight_recommendations.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-argus-text-dim uppercase tracking-wide mb-2">
            Weight Recommendations ({weight_recommendations.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {weight_recommendations.map((rec) => {
              const fieldPath = `quality_engine.weights.${rec.dimension}`;
              const proposal = proposalsByField.get(fieldPath);
              return (
                <WeightRecommendationCard
                  key={rec.dimension}
                  recommendation={rec}
                  proposalId={proposal?.proposal_id ?? ''}
                  status={proposal?.status ?? 'PENDING'}
                  humanNotes={proposal?.human_notes ?? null}
                  onApprove={handleApprove}
                  onDismiss={handleDismiss}
                  onRevert={handleRevert}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Threshold Recommendations */}
      {threshold_recommendations.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-argus-text-dim uppercase tracking-wide mb-2">
            Threshold Recommendations ({threshold_recommendations.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {threshold_recommendations.map((rec) => {
              const fieldPath = `quality_engine.thresholds.${rec.grade}`;
              const proposal = proposalsByField.get(fieldPath);
              return (
                <ThresholdRecommendationCard
                  key={rec.grade}
                  recommendation={rec}
                  proposalId={proposal?.proposal_id ?? ''}
                  status={proposal?.status ?? 'PENDING'}
                  humanNotes={proposal?.human_notes ?? null}
                  onApprove={handleApprove}
                  onDismiss={handleDismiss}
                  onRevert={handleRevert}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* No recommendations */}
      {pendingCount === 0 && (
        <Card>
          <div className="text-center py-6 text-argus-text-dim text-sm">
            Analysis complete — no recommendations at this time.
          </div>
        </Card>
      )}
    </div>
  );
}
