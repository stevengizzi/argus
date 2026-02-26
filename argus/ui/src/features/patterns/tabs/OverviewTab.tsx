/**
 * Overview tab for Pattern Library detail view.
 *
 * Shows:
 * - Current strategy parameters (view-only)
 * - Strategy documentation list (clickable to open modal)
 */

import { useState } from 'react';
import { FileText, ChevronRight } from 'lucide-react';
import { Card } from '../../../components/Card';
import { Skeleton } from '../../../components/Skeleton';
import { DocumentModal } from '../../../components/DocumentModal';
import { useStrategySpec } from '../../../hooks/useStrategySpec';
import type { StrategyInfo, StrategyDocument } from '../../../api/types';

interface OverviewTabProps {
  strategy: StrategyInfo;
}

/**
 * Format a config parameter name for display.
 *
 * Examples:
 * - orb_window_minutes → "ORB Window (min)"
 * - target_1_r → "Target 1 R"
 * - max_loss_per_trade_pct → "Max Loss Per Trade %"
 * - volume_threshold_rvol → "Volume Threshold (RVOL)"
 */
function formatParamName(key: string): string {
  // Special case mappings for known parameters
  const specialCases: Record<string, string> = {
    orb_window_minutes: 'ORB Window (min)',
    target_1_r: 'Target 1 (R)',
    target_2_r: 'Target 2 (R)',
    time_stop_minutes: 'Time Stop (min)',
    volume_threshold_rvol: 'Volume Threshold (RVOL)',
    chase_protection_pct: 'Chase Protection %',
    breakout_volume_multiplier: 'Breakout Volume Multiplier',
    min_range_atr_ratio: 'Min Range ATR Ratio',
    max_range_atr_ratio: 'Max Range ATR Ratio',
    max_loss_per_trade_pct: 'Max Loss Per Trade %',
    max_trades_per_day: 'Max Trades Per Day',
    earliest_entry: 'Earliest Entry',
    latest_entry: 'Latest Entry',
    asset_class: 'Asset Class',
    stop_placement: 'Stop Placement',
    enabled: 'Enabled',
  };

  if (key in specialCases) {
    return specialCases[key];
  }

  // Generic transformation: snake_case to Title Case
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
    .replace(/ Pct$/, ' %')
    .replace(/ R$/, ' (R)');
}

/**
 * Format a config parameter value for display.
 */
function formatParamValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '—';
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }

  if (typeof value === 'number') {
    // Percentages
    if (value < 1 && value > 0) {
      return `${(value * 100).toFixed(1)}%`;
    }
    // Large numbers
    if (Number.isInteger(value)) {
      return value.toLocaleString();
    }
    // Decimals
    return value.toFixed(2);
  }

  if (typeof value === 'string') {
    return value;
  }

  // For objects or arrays, stringify
  return JSON.stringify(value);
}

/**
 * Format ISO date string to readable format (MMM DD, YYYY).
 */
function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function OverviewTab({ strategy }: OverviewTabProps) {
  const { data: specData, isLoading: isLoadingSpec, isError } = useStrategySpec(strategy.strategy_id);
  const [selectedDocument, setSelectedDocument] = useState<StrategyDocument | null>(null);

  const configEntries = Object.entries(strategy.config_summary || {}).filter(
    ([, value]) => value !== null && value !== undefined
  );

  return (
    <div className="space-y-6">
      {/* Section 1: Parameter Table */}
      <Card>
        <div className="mb-4">
          <h3 className="text-base font-medium text-argus-text mb-1">Current Parameters</h3>
          <p className="text-xs text-argus-text-dim">
            View-only. Parameter editing available with AI Layer (Sprint 22).
          </p>
        </div>

        {configEntries.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-argus-border">
                  <th className="text-left text-argus-text-dim font-medium py-2 pr-4">
                    Parameter
                  </th>
                  <th className="text-right text-argus-text-dim font-medium py-2">Value</th>
                </tr>
              </thead>
              <tbody>
                {configEntries.map(([key, value]) => (
                  <tr key={key} className="border-b border-argus-border/50 last:border-0">
                    <td className="text-argus-text py-2 pr-4">{formatParamName(key)}</td>
                    <td className="text-argus-text tabular-nums py-2 text-right font-mono text-xs">
                      {formatParamValue(value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-argus-text-dim">No configuration parameters available.</p>
        )}
      </Card>

      {/* Section 2: Strategy Documentation List */}
      <Card>
        <h3 className="text-base font-medium text-argus-text mb-4">Strategy Documentation</h3>

        {isLoadingSpec && (
          <div className="space-y-3" data-testid="spec-loading">
            <Skeleton className="h-14" />
          </div>
        )}

        {!isLoadingSpec && isError && (
          <p className="text-sm text-argus-text-dim">Unable to load strategy documentation.</p>
        )}

        {!isLoadingSpec && !isError && specData?.documents && specData.documents.length > 0 && (
          <div className="space-y-2">
            {specData.documents.map((doc) => (
              <button
                key={doc.doc_id}
                onClick={() => setSelectedDocument(doc)}
                className="w-full flex items-center gap-3 p-3 rounded-lg bg-argus-surface-2 hover:bg-argus-surface-3 transition-colors text-left"
              >
                <FileText className="w-5 h-5 text-argus-text-dim flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-argus-text truncate">{doc.title}</div>
                  <div className="text-xs text-argus-text-dim">
                    {doc.word_count.toLocaleString()} words · {doc.reading_time_min} min read · Updated {formatDate(doc.last_modified)}
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-argus-text-dim flex-shrink-0" />
              </button>
            ))}
          </div>
        )}

        {!isLoadingSpec && !isError && (!specData?.documents || specData.documents.length === 0) && (
          <p className="text-sm text-argus-text-dim">No documentation available for this strategy.</p>
        )}
      </Card>

      {/* Document Modal */}
      <DocumentModal
        document={selectedDocument}
        isOpen={selectedDocument !== null}
        onClose={() => setSelectedDocument(null)}
      />
    </div>
  );
}
