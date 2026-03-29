/**
 * Strategy Health Bands — per-strategy horizontal bars showing trailing metrics.
 *
 * Displays Sharpe, win rate, and expectancy for each strategy with color encoding:
 * green (above baseline), amber (near baseline), red (below baseline).
 * Purely observational — no throttle/boost actions (deferred to Sprint 40).
 *
 * Sprint 28, Session 6c.
 */

import { useMemo } from 'react';
import { Card } from '../Card';
import { CardHeader } from '../CardHeader';
import type { LearningReport, WeightRecommendation } from '../../api/learningApi';

interface StrategyHealthBandsProps {
  report: LearningReport | null;
}

interface StrategyMetrics {
  strategyId: string;
  sharpe: number | null;
  winRate: number | null;
  expectancy: number | null;
  tradeCount: number;
}

/** Baseline thresholds for color encoding. */
const BASELINES = {
  sharpe: { good: 1.0, warn: 0.5 },
  winRate: { good: 0.5, warn: 0.35 },
  expectancy: { good: 0.3, warn: 0.0 },
} as const;

type MetricKey = keyof typeof BASELINES;

function getBarColor(value: number | null, metric: MetricKey): string {
  if (value === null) return 'bg-argus-surface-2';
  const { good, warn } = BASELINES[metric];
  if (value >= good) return 'bg-emerald-500';
  if (value >= warn) return 'bg-amber-500';
  return 'bg-red-500';
}

function getBarWidth(value: number | null, metric: MetricKey): number {
  if (value === null) return 0;
  // Normalize to 0–100% range based on metric
  if (metric === 'winRate') return Math.min(100, Math.max(0, value * 100));
  if (metric === 'sharpe') return Math.min(100, Math.max(0, (value / 3) * 100));
  // expectancy: scale around -1 to +2 range
  return Math.min(100, Math.max(0, ((value + 1) / 3) * 100));
}

function formatMetricValue(value: number | null, metric: MetricKey): string {
  if (value === null) return '--';
  if (metric === 'winRate') return `${(value * 100).toFixed(1)}%`;
  return value.toFixed(2);
}

function metricLabel(metric: MetricKey): string {
  if (metric === 'sharpe') return 'Sharpe';
  if (metric === 'winRate') return 'Win Rate';
  return 'Expectancy';
}

/**
 * Extract per-strategy metrics from weight recommendations.
 * Groups by strategy dimension prefix and aggregates available metrics.
 */
function extractStrategyMetrics(
  recommendations: WeightRecommendation[]
): StrategyMetrics[] {
  const strategyMap = new Map<string, StrategyMetrics>();

  for (const rec of recommendations) {
    // Dimension names follow pattern: "strategy_name.metric" or just "dimension"
    // Use sample_size as proxy for trade count
    const parts = rec.dimension.split('.');
    const strategyId = parts.length > 1 ? parts[0] : rec.dimension;

    if (!strategyMap.has(strategyId)) {
      strategyMap.set(strategyId, {
        strategyId,
        sharpe: null,
        winRate: null,
        expectancy: null,
        tradeCount: rec.sample_size,
      });
    }

    const entry = strategyMap.get(strategyId)!;
    entry.tradeCount = Math.max(entry.tradeCount, rec.sample_size);

    // Use correlation values as health indicators when available
    if (rec.correlation_trade_source !== null) {
      // Map correlation magnitude to a health-like metric
      entry.sharpe = rec.correlation_trade_source;
    }
  }

  return Array.from(strategyMap.values());
}

export function StrategyHealthBands({ report }: StrategyHealthBandsProps) {
  const strategies = useMemo(() => {
    if (!report) return [];
    return extractStrategyMetrics(report.weight_recommendations);
  }, [report]);

  // Empty state
  if (!report || strategies.length === 0) {
    return (
      <Card>
        <CardHeader title="Strategy Health" />
        <div className="text-center py-8" data-testid="health-bands-empty">
          <p className="text-argus-text-dim text-sm">
            {!report
              ? 'Strategy health data will appear after the first analysis'
              : 'Not enough data for strategy health metrics yet'}
          </p>
        </div>
      </Card>
    );
  }

  const metrics: MetricKey[] = ['sharpe', 'winRate', 'expectancy'];

  return (
    <Card>
      <CardHeader title="Strategy Health" />
      <div className="space-y-4" data-testid="health-bands">
        {strategies.map((strategy) => (
          <div key={strategy.strategyId} className="space-y-1.5">
            {/* Strategy name + trade count */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-argus-text">
                {strategy.strategyId.replace(/_/g, ' ')}
              </span>
              <span className="text-xs text-argus-text-dim tabular-nums">
                {strategy.tradeCount} trades
              </span>
            </div>

            {/* Metric bars */}
            <div className="space-y-1">
              {metrics.map((metric) => {
                const value = strategy[metric];
                const barColor = getBarColor(value, metric);
                const barWidth = getBarWidth(value, metric);
                const displayValue = formatMetricValue(value, metric);

                return (
                  <div
                    key={metric}
                    className="flex items-center gap-2 group"
                    title={`${metricLabel(metric)}: ${displayValue} (${strategy.tradeCount} trades)`}
                  >
                    <span className="text-[10px] text-argus-text-dim w-16 shrink-0">
                      {metricLabel(metric)}
                    </span>
                    <div className="flex-1 h-2 bg-argus-surface-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${barColor}`}
                        style={{ width: `${barWidth}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-argus-text-dim tabular-nums w-12 text-right">
                      {displayValue}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
