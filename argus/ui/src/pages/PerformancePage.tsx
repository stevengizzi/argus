/**
 * Performance analytics page with charts and metrics.
 *
 * Shows equity curve, daily P&L histogram, metrics grid, and strategy breakdown.
 * Period selector controls the time range for all data.
 *
 * Sprint 21d: Refactored into tabbed layout with 5 sub-views:
 * - Overview: existing content (MetricsGrid, EquityCurve, DailyPnlChart, StrategyBreakdown)
 * - Heatmaps: TradeActivityHeatmap, CalendarPnlView
 * - Distribution: RMultipleHistogram, RiskWaterfall
 * - Portfolio: PortfolioTreemap, CorrelationMatrix
 * - Replay: TradeReplay
 *
 * Uses local state for period to prevent data flash during page exit animations.
 * Containers/headers stay stable during period changes - only data values transition.
 *
 * With keepPreviousData in TanStack Query:
 * - isLoading is only true on the very first load (no cache at all)
 * - isFetching is true during period changes while previous data is shown
 * - data contains placeholder (previous period's data) during transitions
 */

import { Component, type ReactNode, useState, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp } from 'lucide-react';
import { usePerformance, usePreviousPeriodPerformance } from '../hooks/usePerformance';
import { Card } from '../components/Card';
import { SegmentedTab } from '../components/SegmentedTab';
import {
  PeriodSelector,
  MetricsGrid,
  EquityCurve,
  DailyPnlChart,
  StrategyBreakdown,
  PerformanceSkeleton,
} from '../features/performance';
import { TradeActivityHeatmap } from '../features/performance/TradeActivityHeatmap';
import { CalendarPnlView } from '../features/performance/CalendarPnlView';
import { RMultipleHistogram } from '../features/performance/RMultipleHistogram';
import { RiskWaterfall } from '../features/performance/RiskWaterfall';
import { PortfolioTreemap } from '../features/performance/PortfolioTreemap';
import { CorrelationMatrix } from '../features/performance/CorrelationMatrix';
import { TradeReplay } from '../features/performance/TradeReplay';
import { staggerContainer, staggerItem } from '../utils/motion';
import type { PerformancePeriod } from '../api/types';

// Performance tabs
type PerformanceTab = 'overview' | 'heatmaps' | 'distribution' | 'portfolio' | 'replay';

const TAB_SEGMENTS = [
  { label: 'Overview', value: 'overview' },
  { label: 'Heatmaps', value: 'heatmaps' },
  { label: 'Distribution', value: 'distribution' },
  { label: 'Portfolio', value: 'portfolio' },
  { label: 'Replay', value: 'replay' },
];

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

  // Tab state
  const [activeTab, setActiveTab] = useState<PerformanceTab>('overview');

  // Comparison state
  const [comparisonEnabled, setComparisonEnabled] = useState(false);

  const { data, isLoading, error, isFetching } = usePerformance(period);

  // Fetch previous period data for comparison (only when enabled and not "all" period)
  const { data: comparisonData } = usePreviousPeriodPerformance(
    period,
    comparisonEnabled && period !== 'all'
  );

  // Handle comparison toggle from EquityCurve
  const handleComparisonToggle = useCallback((enabled: boolean) => {
    setComparisonEnabled(enabled);
  }, []);

  // Keyboard shortcuts for tab navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input, textarea, or contenteditable
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'o':
          setActiveTab('overview');
          break;
        case 'h':
          setActiveTab('heatmaps');
          break;
        case 'd':
          setActiveTab('distribution');
          break;
        case 'p':
          setActiveTab('portfolio');
          break;
        case 'r':
          setActiveTab('replay');
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // First load (no cache at all) — show skeleton
  // With keepPreviousData, isLoading is only true when there's truly no data
  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          selectedPeriod={period}
          onPeriodChange={setPeriod}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
        <PerformanceSkeleton />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="space-y-6">
        <PageHeader
          selectedPeriod={period}
          onPeriodChange={setPeriod}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
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
        <PageHeader
          selectedPeriod={period}
          onPeriodChange={setPeriod}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
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
      {/* Page header with period selector and tabs */}
      <motion.div variants={staggerItem}>
        <PageHeader
          selectedPeriod={period}
          onPeriodChange={setPeriod}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      </motion.div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <OverviewTabContent
          data={data}
          isFetching={isFetching}
          period={period}
          comparisonData={comparisonData?.daily_pnl}
          onComparisonToggle={handleComparisonToggle}
        />
      )}

      {activeTab === 'heatmaps' && (
        <HeatmapsTabContent period={period} dailyPnl={data.daily_pnl} />
      )}

      {activeTab === 'distribution' && (
        <DistributionTabContent period={period} />
      )}

      {activeTab === 'portfolio' && (
        <PortfolioTabContent period={period} />
      )}

      {activeTab === 'replay' && (
        <ReplayTabContent period={period} />
      )}
    </motion.div>
  );
}

/** Page header with title, period selector, and tabs */
interface PageHeaderProps {
  selectedPeriod: PerformancePeriod;
  onPeriodChange: (period: PerformancePeriod) => void;
  activeTab: PerformanceTab;
  onTabChange: (tab: PerformanceTab) => void;
}

function PageHeader({ selectedPeriod, onPeriodChange, activeTab, onTabChange }: PageHeaderProps) {
  return (
    <div className="space-y-4">
      {/* Title and period selector */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <TrendingUp className="w-6 h-6 text-argus-accent" />
          <h1 className="text-xl font-semibold text-argus-text">Performance</h1>
        </div>
        <PeriodSelector selectedPeriod={selectedPeriod} onPeriodChange={onPeriodChange} />
      </div>

      {/* Tab navigation */}
      <SegmentedTab
        segments={TAB_SEGMENTS}
        activeValue={activeTab}
        onChange={(value) => onTabChange(value as PerformanceTab)}
        size="sm"
        layoutId="performance-tabs"
      />
    </div>
  );
}

/** Overview tab - existing content */
interface OverviewTabProps {
  data: NonNullable<ReturnType<typeof usePerformance>['data']>;
  isFetching: boolean;
  period: PerformancePeriod;
  comparisonData?: Array<{ date: string; pnl: number; trades: number }>;
  onComparisonToggle?: (enabled: boolean) => void;
}

function OverviewTabContent({
  data,
  isFetching,
  period,
  comparisonData,
  onComparisonToggle,
}: OverviewTabProps) {
  // Show comparison toggle for all periods except "all"
  const showComparison = period !== 'all';

  return (
    <motion.div
      className="space-y-4 md:space-y-6"
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
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
          <EquityCurve
            dailyPnl={data.daily_pnl}
            isTransitioning={isFetching}
            period={period}
            showComparison={showComparison}
            comparisonData={comparisonData}
            onComparisonToggle={onComparisonToggle}
          />
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

/** Heatmaps tab - Trade Activity Heatmap + Calendar P&L */
interface HeatmapsTabProps {
  period: PerformancePeriod;
  dailyPnl: Array<{ date: string; pnl: number; trades: number }>;
}

function HeatmapsTabContent({ period, dailyPnl }: HeatmapsTabProps) {
  return (
    <motion.div
      className="space-y-4 md:space-y-6"
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      <motion.div variants={staggerItem}>
        <TradeActivityHeatmap period={period} />
      </motion.div>
      <motion.div variants={staggerItem}>
        <CalendarPnlView dailyPnl={dailyPnl} />
      </motion.div>
    </motion.div>
  );
}

/** Distribution tab - R-Multiple Histogram + Risk Waterfall */
interface DistributionTabProps {
  period: PerformancePeriod;
}

function DistributionTabContent({ period }: DistributionTabProps) {
  return (
    <motion.div
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      {/* Side by side on desktop (≥1024px), stacked on tablet/mobile */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 items-stretch">
        <motion.div variants={staggerItem} className="lg:col-span-1 h-full">
          <RMultipleHistogram period={period} fullHeight />
        </motion.div>
        <motion.div variants={staggerItem} className="lg:col-span-1 h-full">
          <RiskWaterfall fullHeight />
        </motion.div>
      </div>
    </motion.div>
  );
}

/** Portfolio tab - Treemap + Correlation Matrix */
interface PortfolioTabProps {
  period: PerformancePeriod;
}

function PortfolioTabContent({ period }: PortfolioTabProps) {
  return (
    <motion.div
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      {/* Side by side on desktop (≥1024px): 60% treemap, 40% correlation */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 md:gap-6 items-stretch">
        <motion.div variants={staggerItem} className="lg:col-span-3 h-full">
          <PortfolioTreemap fullHeight />
        </motion.div>
        <motion.div variants={staggerItem} className="lg:col-span-2 h-full">
          <CorrelationMatrix period={period} fullHeight />
        </motion.div>
      </div>
    </motion.div>
  );
}

/** Replay tab - Animated trade walkthrough */
interface ReplayTabProps {
  period: PerformancePeriod;
}

function ReplayTabContent({ period }: ReplayTabProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <TradeReplay period={period} />
    </motion.div>
  );
}
