/**
 * Performance analytics page with charts and metrics.
 *
 * Shows equity curve, daily P&L histogram, metrics grid, and strategy breakdown.
 * Period selector controls the time range for all data.
 *
 * Uses local state for period to prevent data flash during page exit animations.
 * Containers/headers stay stable during period changes - only data values transition.
 *
 * With keepPreviousData in TanStack Query:
 * - isLoading is only true on the very first load (no cache at all)
 * - isFetching is true during period changes while previous data is shown
 * - data contains placeholder (previous period's data) during transitions
 */

import { Component, type ReactNode, useState } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp } from 'lucide-react';
import { usePerformance } from '../hooks/usePerformance';
import { Card } from '../components/Card';
import {
  PeriodSelector,
  MetricsGrid,
  EquityCurve,
  DailyPnlChart,
  StrategyBreakdown,
  PerformanceSkeleton,
} from '../features/performance';
import { staggerContainer, staggerItem } from '../utils/motion';
import type { PerformancePeriod } from '../api/types';

// Error boundary to catch chart rendering errors
interface ErrorBoundaryProps {
  children: ReactNode;
  fallback: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ChartErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <Card>
          <div className="text-center py-8">
            <p className="text-argus-loss">Chart failed to render</p>
            <p className="text-argus-text-dim text-xs mt-2">
              {this.state.error?.message || 'Unknown error'}
            </p>
          </div>
        </Card>
      );
    }
    return this.props.children;
  }
}

export function PerformancePage() {
  // Local state initialized from URL - immune to URL changes during exit animation
  const [period, setPeriod] = useState<PerformancePeriod>(() => {
    const params = new URLSearchParams(window.location.search);
    return (params.get('period') as PerformancePeriod) || 'month';
  });

  const { data, isLoading, error, isFetching } = usePerformance(period);

  // First load (no cache at all) — show skeleton
  // With keepPreviousData, isLoading is only true when there's truly no data
  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader selectedPeriod={period} onPeriodChange={setPeriod} />
        <PerformanceSkeleton />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="space-y-6">
        <PageHeader selectedPeriod={period} onPeriodChange={setPeriod} />
        <Card>
          <div className="text-center py-8">
            <TrendingUp className="w-8 h-8 text-argus-loss mx-auto mb-4" />
            <p className="text-argus-text-dim">Failed to load performance data</p>
            <p className="text-argus-text-dim text-xs mt-2">{error.message}</p>
            <button
              onClick={() => window.location.reload()}
              className="text-argus-accent hover:underline text-sm mt-4"
            >
              Try again
            </button>
          </div>
        </Card>
      </div>
    );
  }

  if (!data || data.metrics.total_trades === 0) {
    return (
      <div className="space-y-6">
        <PageHeader selectedPeriod={period} onPeriodChange={setPeriod} />
        <Card>
          <div className="text-center py-8">
            <TrendingUp className="w-8 h-8 text-argus-text-dim mx-auto mb-4" />
            <p className="text-argus-text-dim">No trades for this period</p>
          </div>
        </Card>
      </div>
    );
  }

  // Main render — containers are always stable, isFetching dims data during transition
  return (
    <motion.div
      className="space-y-4 md:space-y-6"
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      {/* Page header with period selector */}
      <motion.div
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
        variants={staggerItem}
      >
        <div className="flex items-center gap-3">
          <TrendingUp className="w-6 h-6 text-argus-accent" />
          <h1 className="text-xl font-semibold text-argus-text">Performance</h1>
        </div>
        <PeriodSelector selectedPeriod={period} onPeriodChange={setPeriod} />
      </motion.div>

      {/* Metrics grid — pass isFetching for subtle transition */}
      <motion.div variants={staggerItem}>
        <MetricsGrid metrics={data.metrics} isTransitioning={isFetching} />
      </motion.div>

      {/* Charts — pass isFetching for subtle transition */}
      <motion.div variants={staggerItem}>
        <ChartErrorBoundary
          fallback={
            <Card>
              <div className="h-[300px] flex items-center justify-center text-argus-text-dim">
                Equity chart unavailable
              </div>
            </Card>
          }
        >
          <EquityCurve dailyPnl={data.daily_pnl} isTransitioning={isFetching} />
        </ChartErrorBoundary>
      </motion.div>
      <motion.div variants={staggerItem}>
        <ChartErrorBoundary
          fallback={
            <Card>
              <div className="h-[250px] flex items-center justify-center text-argus-text-dim">
                Daily P&L chart unavailable
              </div>
            </Card>
          }
        >
          <DailyPnlChart dailyPnl={data.daily_pnl} isTransitioning={isFetching} />
        </ChartErrorBoundary>
      </motion.div>

      {/* Strategy breakdown */}
      <motion.div variants={staggerItem}>
        <StrategyBreakdown byStrategy={data.by_strategy} isTransitioning={isFetching} />
      </motion.div>
    </motion.div>
  );
}

/** Page header for loading/error states */
interface PageHeaderProps {
  selectedPeriod: PerformancePeriod;
  onPeriodChange: (period: PerformancePeriod) => void;
}

function PageHeader({ selectedPeriod, onPeriodChange }: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div className="flex items-center gap-3">
        <TrendingUp className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">Performance</h1>
      </div>
      <PeriodSelector selectedPeriod={selectedPeriod} onPeriodChange={onPeriodChange} />
    </div>
  );
}
