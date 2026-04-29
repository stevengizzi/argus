/**
 * Dashboard page - main command post view.
 *
 * Sprint 32.8 Session 2: Dense 4-row layout — vitals, allocation,
 * positions + timeline + quality, AI + learning. No scroll on 1080p.
 *
 * Sprint 21d Dashboard Summary: Uses aggregate endpoint for instant card loading.
 * - Single `useDashboardSummary()` hook fetches all dashboard data in one request
 * - VitalsStrip and TodayStats section receive data as props (no individual loading states)
 *
 * Layout (desktop, ≥1024px):
 *   Row 1: VitalsStrip (equity, P&L, today's stats, VIX) — full width
 *   Row 2: StrategyDeploymentBar — full width, ~40px
 *   Row 3: OpenPositions (70%) | SessionTimeline + SignalQualityPanel stacked (30%)
 *   Row 4: AIInsightCard (50%) | LearningDashboardCard (50%)
 *
 * Tablet (640–1023px): stacked layout, all sections full width.
 * Phone (<640px): single-column stacked.
 *
 * GoalTracker and UniverseStatusCard are NOT rendered on this page.
 * The components themselves are not deleted — they may be used elsewhere.
 */

import { motion } from 'framer-motion';
import { useSearchParams } from 'react-router-dom';
import {
  AIInsightCard,
  MarketStatusCard,
  SessionTimeline,
  OpenPositions,
  SessionSummaryCard,
  OrchestratorStatusStrip,
  StrategyDeploymentBar,
  PreMarketLayout,
  SignalQualityPanel,
  VitalsStrip,
} from '../features/dashboard';
import { LearningDashboardCard } from '../components/learning/LearningDashboardCard';
import { WatchlistSidebar } from '../features/watchlist';
import { staggerContainer, staggerItem } from '../utils/motion';
import { useIsMultiColumn, useMediaQuery } from '../hooks/useMediaQuery';
import { useDashboardSummary } from '../hooks/useDashboardSummary';
import { useCopilotContext } from '../hooks/useCopilotContext';

export function DashboardPage() {
  const isMultiColumn = useIsMultiColumn();
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const { data: summaryData } = useDashboardSummary();
  const [searchParams] = useSearchParams();

  // Register Copilot context
  useCopilotContext('Dashboard', () => ({
    equity: summaryData?.account?.equity ?? 0,
    dailyPnl: summaryData?.account?.daily_pnl ?? 0,
    regime: summaryData?.orchestrator?.regime ?? 'unknown',
    activeStrategyCount: summaryData?.orchestrator?.active_strategy_count ?? 0,
    marketStatus: summaryData?.market?.status ?? 'unknown',
    deployedPct: summaryData?.orchestrator?.deployed_pct ?? 0,
  }));

  // Check for pre-market: either real market status or dev mode override
  // Dev mode: use localStorage.setItem('argus_premarket', 'true') in console
  const isPreMarket =
    summaryData?.market.status === 'pre_market' ||
    searchParams.get('premarket') === 'true' ||
    (typeof window !== 'undefined' && localStorage.getItem('argus_premarket') === 'true');

  // Render pre-market layout when applicable
  if (isPreMarket) {
    if (isDesktop) {
      return (
        <div className="flex gap-6 -mr-6 -mb-6">
          <div className="flex-1 min-w-0 flex flex-col gap-3">
            <PreMarketLayout />
          </div>
          <WatchlistSidebar className="sticky top-0 h-[calc(100vh-3rem)] flex-shrink-0" />
        </div>
      );
    }

    return (
      <>
        <PreMarketLayout />
        <WatchlistSidebar />
      </>
    );
  }

  // Phone: flat vertical stagger, all cards as direct children
  if (!isMultiColumn) {
    return (
      <>
        <motion.div
          key="dashboard-single"
          className="space-y-4"
          variants={staggerContainer(0.08)}
          initial="hidden"
          animate="show"
        >
          <motion.div variants={staggerItem}>
            <OrchestratorStatusStrip />
          </motion.div>

          <motion.div variants={staggerItem}>
            <StrategyDeploymentBar />
          </motion.div>

          <SessionSummaryCard />

          <motion.div variants={staggerItem}>
            <VitalsStrip todayStats={summaryData?.today_stats} />
          </motion.div>

          <motion.div variants={staggerItem}><MarketStatusCard /></motion.div>

          <motion.div variants={staggerItem}><OpenPositions /></motion.div>

          <motion.div variants={staggerItem}><SessionTimeline /></motion.div>
          <motion.div variants={staggerItem}><SignalQualityPanel /></motion.div>

          <motion.div variants={staggerItem}><AIInsightCard /></motion.div>
          <motion.div variants={staggerItem}><LearningDashboardCard /></motion.div>
        </motion.div>

        <WatchlistSidebar />
      </>
    );
  }

  // Desktop: dense 4-row layout + right sidebar
  if (isDesktop) {
    return (
      <div className="flex gap-6 -mr-6 -mb-6">
        {/* Main content area */}
        <motion.div
          key="dashboard-desktop"
          className="flex-1 min-w-0 flex flex-col gap-3 h-[calc(100vh-3rem)]"
          variants={staggerContainer(0.06)}
          initial="hidden"
          animate="show"
        >
          {/* Row 1: VitalsStrip — full width */}
          <motion.div variants={staggerItem}>
            <VitalsStrip todayStats={summaryData?.today_stats} />
          </motion.div>

          {/* Row 2: Strategy allocation bar — full width, ~40px */}
          <motion.div variants={staggerItem}>
            <StrategyDeploymentBar />
          </motion.div>

          <SessionSummaryCard />

          {/* Row 3: Positions (70%) | Timeline + Quality stacked (30%) */}
          <motion.div
            className="flex gap-3 flex-1 min-h-0"
            variants={staggerItem}
          >
            {/* Left: Positions table — 70% */}
            <div className="flex-[7] min-w-0 h-full">
              <OpenPositions />
            </div>

            {/* Right: SessionTimeline (top) + SignalQualityPanel (bottom) — 30% */}
            <div className="flex-[3] flex flex-col gap-3 min-w-0">
              <div className="flex-1 min-h-0">
                <SessionTimeline />
              </div>
              <div className="flex-1 min-h-0">
                <SignalQualityPanel />
              </div>
            </div>
          </motion.div>

          {/* Row 4: AI Insight (50%) | Learning Loop (50%) — matched heights */}
          <motion.div
            className="grid grid-cols-2 gap-3 items-stretch"
            variants={staggerItem}
          >
            <div className="flex flex-col">
              <AIInsightCard />
            </div>
            <div className="flex flex-col">
              <LearningDashboardCard />
            </div>
          </motion.div>
        </motion.div>

        {/* Watchlist sidebar - sticky on right */}
        <WatchlistSidebar className="sticky top-0 h-[calc(100vh-3rem)] flex-shrink-0" />
      </div>
    );
  }

  // Tablet: stacked layout with floating overlay button
  return (
    <>
      <motion.div
        key="dashboard-tablet"
        className="space-y-4"
        variants={staggerContainer(0.08)}
        initial="hidden"
        animate="show"
      >
        <motion.div variants={staggerItem}>
          <OrchestratorStatusStrip />
        </motion.div>

        <motion.div variants={staggerItem}>
          <StrategyDeploymentBar />
        </motion.div>

        <SessionSummaryCard />

        <motion.div variants={staggerItem}>
          <VitalsStrip todayStats={summaryData?.today_stats} />
        </motion.div>

        <motion.div variants={staggerItem}><MarketStatusCard /></motion.div>

        <motion.div variants={staggerItem}>
          <OpenPositions />
        </motion.div>

        <motion.div variants={staggerItem}><SessionTimeline /></motion.div>
        <motion.div variants={staggerItem}><SignalQualityPanel /></motion.div>

        <motion.div variants={staggerItem}><AIInsightCard /></motion.div>
        <motion.div variants={staggerItem}><LearningDashboardCard /></motion.div>
      </motion.div>

      <WatchlistSidebar />
    </>
  );
}
