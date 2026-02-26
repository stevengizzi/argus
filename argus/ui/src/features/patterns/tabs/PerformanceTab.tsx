/**
 * Performance tab for Pattern Library detail view.
 *
 * Shows strategy-specific performance analytics:
 * - Period selector (Today/Week/Month/All)
 * - 6-metric summary grid
 * - Equity curve (cumulative P&L)
 * - Daily P&L histogram
 *
 * Reuses existing Performance page components where possible.
 */

import { useState } from 'react';
import { Card } from '../../../components/Card';
import { MetricCard } from '../../../components/MetricCard';
import { Skeleton } from '../../../components/Skeleton';
import { PeriodSelector } from '../../performance/PeriodSelector';
import { EquityCurve } from '../../performance/EquityCurve';
import { DailyPnlChart } from '../../performance/DailyPnlChart';
import { usePerformance } from '../../../hooks/usePerformance';
import { formatPercentRaw } from '../../../utils/format';
import type { PerformancePeriod } from '../../../api/types';

interface PerformanceTabProps {
  strategyId: string;
}

export function PerformanceTab({ strategyId }: PerformanceTabProps) {
  const [period, setPeriod] = useState<PerformancePeriod>('month');
  const { data, isLoading, isFetching } = usePerformance(period, strategyId);

  // Show transition state when fetching new period data
  const isTransitioning = isFetching && !isLoading;

  const metrics = data?.metrics;
  const dailyPnl = data?.daily_pnl ?? [];

  // Compute trends for indicators
  const winRatePct = metrics ? metrics.win_rate * 100 : 0;
  const winRateTrend = winRatePct > 50 ? 'up' : winRatePct < 50 ? 'down' : 'neutral';
  const pfTrend = metrics
    ? metrics.profit_factor > 1
      ? 'up'
      : metrics.profit_factor < 1
        ? 'down'
        : 'neutral'
    : 'neutral';
  const sharpeTrend = metrics
    ? metrics.sharpe_ratio > 0
      ? 'up'
      : metrics.sharpe_ratio < 0
        ? 'down'
        : 'neutral'
    : 'neutral';
  const avgRTrend = metrics
    ? metrics.avg_r_multiple > 0
      ? 'up'
      : metrics.avg_r_multiple < 0
        ? 'down'
        : 'neutral'
    : 'neutral';

  return (
    <div className="space-y-4">
      {/* Period Selector - controlled mode, no URL sync */}
      <PeriodSelector
        selectedPeriod={period}
        onPeriodChange={setPeriod}
        className="justify-start"
      />

      {/* Metrics Grid - 6 key metrics */}
      <Card>
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex flex-col items-center gap-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-6 w-12" />
              </div>
            ))}
          </div>
        ) : metrics ? (
          <div
            className={`grid grid-cols-2 sm:grid-cols-3 gap-4 transition-opacity duration-200 ${
              isTransitioning ? 'opacity-40' : 'opacity-100'
            }`}
          >
            <MetricCard label="Trades" value={metrics.total_trades.toString()} />
            <MetricCard
              label="Win Rate"
              value={formatPercentRaw(winRatePct)}
              trend={winRateTrend}
            />
            <MetricCard
              label="Profit Factor"
              value={metrics.profit_factor.toFixed(2)}
              trend={pfTrend}
            />
            <MetricCard
              label="Sharpe"
              value={metrics.sharpe_ratio.toFixed(2)}
              trend={sharpeTrend}
            />
            <MetricCard
              label="Avg R"
              value={`${metrics.avg_r_multiple.toFixed(2)}R`}
              trend={avgRTrend}
            />
            <MetricCard
              label="Max DD"
              value={formatPercentRaw(Math.abs(metrics.max_drawdown_pct))}
              subValue="drawdown"
            />
          </div>
        ) : (
          <p className="text-sm text-argus-text-dim text-center py-4">
            No performance data available
          </p>
        )}
      </Card>

      {/* Equity Curve */}
      {isLoading ? (
        <Card>
          <Skeleton className="h-4 w-24 mb-4" />
          <Skeleton className="h-[180px] w-full" />
        </Card>
      ) : (
        <EquityCurve
          dailyPnl={dailyPnl}
          isTransitioning={isTransitioning}
          className="[&_.p-4]:p-3 [&_.p-4]:pb-0"
        />
      )}

      {/* Daily P&L Histogram */}
      {isLoading ? (
        <Card>
          <Skeleton className="h-4 w-20 mb-4" />
          <Skeleton className="h-[160px] w-full" />
        </Card>
      ) : (
        <DailyPnlChart
          dailyPnl={dailyPnl}
          isTransitioning={isTransitioning}
          className="[&_.p-4]:p-3 [&_.p-4]:pb-0"
        />
      )}

      {/* Strategy Comparison Placeholder */}
      <Card>
        <p className="text-sm text-argus-text-dim text-center py-3">
          Strategy comparison coming soon
        </p>
      </Card>
    </div>
  );
}
