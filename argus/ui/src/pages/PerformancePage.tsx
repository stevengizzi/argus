/**
 * Performance analytics page with charts and metrics.
 *
 * Shows equity curve, daily P&L histogram, metrics grid, and strategy breakdown.
 * Period selector controls the time range for all data.
 */

import { Component, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp } from 'lucide-react';
import { usePerformance } from '../hooks/usePerformance';
import { useSelectedPeriod } from '../hooks/useSelectedPeriod';
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
  const period = useSelectedPeriod();
  const { data, isLoading, error } = usePerformance(period);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader />
        <PerformanceSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader />
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
        <PageHeader />
        <Card>
          <div className="text-center py-8">
            <TrendingUp className="w-8 h-8 text-argus-text-dim mx-auto mb-4" />
            <p className="text-argus-text-dim">No trades for this period</p>
          </div>
        </Card>
      </div>
    );
  }

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
        <PeriodSelector />
      </motion.div>

      {/* Metrics grid */}
      <motion.div variants={staggerItem}>
        <MetricsGrid metrics={data.metrics} />
      </motion.div>

      {/* Charts - wrapped in error boundary */}
      <motion.div variants={staggerItem}>
        <ChartErrorBoundary fallback={<Card><div className="h-[300px] flex items-center justify-center text-argus-text-dim">Equity chart unavailable</div></Card>}>
          <EquityCurve dailyPnl={data.daily_pnl} />
        </ChartErrorBoundary>
      </motion.div>
      <motion.div variants={staggerItem}>
        <ChartErrorBoundary fallback={<Card><div className="h-[250px] flex items-center justify-center text-argus-text-dim">Daily P&L chart unavailable</div></Card>}>
          <DailyPnlChart dailyPnl={data.daily_pnl} />
        </ChartErrorBoundary>
      </motion.div>

      {/* Strategy breakdown */}
      <motion.div variants={staggerItem}>
        <StrategyBreakdown byStrategy={data.by_strategy} />
      </motion.div>
    </motion.div>
  );
}

/** Page header without period selector (for loading/error states) */
function PageHeader() {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div className="flex items-center gap-3">
        <TrendingUp className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">Performance</h1>
      </div>
      <PeriodSelector />
    </div>
  );
}
