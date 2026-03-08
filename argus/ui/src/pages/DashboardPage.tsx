/**
 * Dashboard page - main command post view.
 *
 * Sprint 21d Dashboard Summary: Uses aggregate endpoint for instant card loading.
 * - Single `useDashboardSummary()` hook fetches all dashboard data in one request
 * - TodayStats and GoalTracker receive data as props (no individual loading states)
 * - Other cards continue using their own hooks (they're fast enough)
 *
 * Sprint 21d Session 5 (DEC-204): Dashboard scope refinement.
 * - OrchestratorStatusStrip at top (click to Orchestrator page)
 * - StrategyDeploymentBar below status strip
 * - GoalTracker in third position of top row
 * - PreMarketLayout when market_status === 'pre_market' or ?premarket=true
 *
 * Sprint 21d Session 4 (DEC-204): Dashboard scope refinement.
 * - OrchestratorStatusStrip at top (click to Orchestrator page)
 * - Removed RiskAllocationPanel (migrated to Orchestrator page)
 * - Narrowed to ambient awareness: account, P&L, market status, positions, trades, health
 *
 * Responsive grid layout with three breakpoints:
 * - Phone (<640px): Single column stacked layout with flat vertical stagger
 * - Tablet (640-1023px): Two-column grid with grouped stagger
 * - Desktop (>=1024px): Full three-column layout with grouped stagger + watchlist sidebar
 *
 * Stagger animation is responsive:
 * - Multi-column (tablet+): Cards in a row stagger left-to-right within grid groups
 * - Single column (phone): All cards as direct children, stagger top-to-bottom linearly
 *
 * Watchlist sidebar:
 * - Desktop: 280px right sidebar, collapsible
 * - Tablet/Mobile: Floating button opens overlay panel
 */

import { motion } from 'framer-motion';
import { useSearchParams } from 'react-router-dom';
import {
  AccountSummary,
  AIInsightCard,
  DailyPnlCard,
  MarketStatusCard,
  TodayStats,
  SessionTimeline,
  OpenPositions,
  RecentTrades,
  HealthMini,
  SessionSummaryCard,
  OrchestratorStatusStrip,
  StrategyDeploymentBar,
  GoalTracker,
  PreMarketLayout,
  UniverseStatusCard,
} from '../features/dashboard';
import { WatchlistSidebar } from '../features/watchlist';
import { staggerContainer, staggerItem, staggerItemWithChildren } from '../utils/motion';
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
  // Desktop: flex wrapper positions sidebar on right (same as active-market layout)
  // Tablet/Mobile: WatchlistSidebar renders its own FAB + overlay
  if (isPreMarket) {
    if (isDesktop) {
      return (
        <div className="flex gap-6 -mr-6 -mb-6">
          <div className="flex-1 min-w-0">
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
          {/* Orchestrator status strip */}
          <motion.div variants={staggerItem}>
            <OrchestratorStatusStrip />
          </motion.div>

          {/* Strategy deployment bar */}
          <motion.div variants={staggerItem}>
            <StrategyDeploymentBar />
          </motion.div>

          {/* Session summary card - shows after market close with trades */}
          <SessionSummaryCard />

          <motion.div variants={staggerItem}><AccountSummary /></motion.div>
          <motion.div variants={staggerItem}><DailyPnlCard /></motion.div>
          <motion.div variants={staggerItem}><GoalTracker data={summaryData?.goals} useSummaryData /></motion.div>

          {/* 3-card row: Market Status | Today's Stats | Session Timeline */}
          <motion.div variants={staggerItem}><MarketStatusCard /></motion.div>
          <motion.div variants={staggerItem}><TodayStats data={summaryData?.today_stats} useSummaryData /></motion.div>
          <motion.div variants={staggerItem}><SessionTimeline /></motion.div>

          {/* AI Insight card */}
          <motion.div variants={staggerItem}><AIInsightCard /></motion.div>

          {/* Universe status card */}
          <motion.div variants={staggerItem}><UniverseStatusCard /></motion.div>

          <motion.div variants={staggerItem}><OpenPositions /></motion.div>
          <motion.div variants={staggerItem}><RecentTrades /></motion.div>
          <motion.div variants={staggerItem}><HealthMini /></motion.div>
        </motion.div>

        {/* Watchlist overlay for mobile/tablet */}
        <WatchlistSidebar />
      </>
    );
  }

  // Desktop: grid layout with grouped stagger + right sidebar
  if (isDesktop) {
    return (
      <div className="flex gap-6 -mr-6 -mb-6">
        {/* Main content area */}
        <motion.div
          key="dashboard-desktop"
          className="flex-1 min-w-0 space-y-6"
          variants={staggerContainer(0.08)}
          initial="hidden"
          animate="show"
        >
          {/* Orchestrator status strip */}
          <motion.div variants={staggerItem}>
            <OrchestratorStatusStrip />
          </motion.div>

          {/* Strategy deployment bar */}
          <motion.div variants={staggerItem}>
            <StrategyDeploymentBar />
          </motion.div>

          <SessionSummaryCard />

          {/* 3-col row: Account | DailyPnl | GoalTracker */}
          <motion.div
            className="grid grid-cols-3 gap-6"
            variants={staggerItemWithChildren(0.08)}
          >
            <motion.div variants={staggerItem} className="h-full">
              <AccountSummary />
            </motion.div>
            <motion.div variants={staggerItem} className="h-full">
              <DailyPnlCard />
            </motion.div>
            <motion.div variants={staggerItem} className="h-full">
              <GoalTracker data={summaryData?.goals} useSummaryData />
            </motion.div>
          </motion.div>

          {/* 3-col row: Market Status | Today's Stats | Session Timeline */}
          <motion.div
            className="grid grid-cols-3 gap-6"
            variants={staggerItemWithChildren(0.08)}
          >
            <motion.div variants={staggerItem} className="h-full">
              <MarketStatusCard />
            </motion.div>
            <motion.div variants={staggerItem} className="h-full">
              <TodayStats data={summaryData?.today_stats} useSummaryData />
            </motion.div>
            <motion.div variants={staggerItem} className="h-full">
              <SessionTimeline />
            </motion.div>
          </motion.div>

          {/* AI Insight card */}
          <motion.div variants={staggerItem}>
            <AIInsightCard />
          </motion.div>

          {/* Universe status card */}
          <motion.div variants={staggerItem}>
            <UniverseStatusCard />
          </motion.div>

          <motion.div variants={staggerItem}>
            <OpenPositions />
          </motion.div>

          <motion.div
            className="grid grid-cols-2 gap-6"
            variants={staggerItemWithChildren(0.08)}
          >
            <motion.div variants={staggerItem}>
              <RecentTrades />
            </motion.div>
            <motion.div variants={staggerItem}>
              <HealthMini />
            </motion.div>
          </motion.div>
        </motion.div>

        {/* Watchlist sidebar - sticky on right */}
        <WatchlistSidebar className="sticky top-0 h-[calc(100vh-3rem)] flex-shrink-0" />
      </div>
    );
  }

  // Tablet: grid layout with grouped stagger + floating overlay button
  return (
    <>
      <motion.div
        key="dashboard-tablet"
        className="space-y-5"
        variants={staggerContainer(0.08)}
        initial="hidden"
        animate="show"
      >
        {/* Orchestrator status strip */}
        <motion.div variants={staggerItem}>
          <OrchestratorStatusStrip />
        </motion.div>

        {/* Strategy deployment bar */}
        <motion.div variants={staggerItem}>
          <StrategyDeploymentBar />
        </motion.div>

        <SessionSummaryCard />

        <motion.div
          className="grid grid-cols-2 gap-5"
          variants={staggerItemWithChildren(0.08)}
        >
          <motion.div variants={staggerItem} className="h-full">
            <AccountSummary />
          </motion.div>
          <motion.div variants={staggerItem} className="h-full">
            <DailyPnlCard />
          </motion.div>
        </motion.div>

        {/* GoalTracker - full width on tablet */}
        <motion.div variants={staggerItem}>
          <GoalTracker data={summaryData?.goals} useSummaryData />
        </motion.div>

        {/* 3-card row: Market Status | Today's Stats | Session Timeline */}
        <motion.div
          className="grid grid-cols-3 gap-5"
          variants={staggerItemWithChildren(0.08)}
        >
          <motion.div variants={staggerItem} className="h-full">
            <MarketStatusCard />
          </motion.div>
          <motion.div variants={staggerItem} className="h-full">
            <TodayStats data={summaryData?.today_stats} useSummaryData />
          </motion.div>
          <motion.div variants={staggerItem} className="h-full">
            <SessionTimeline />
          </motion.div>
        </motion.div>

        {/* AI Insight card */}
        <motion.div variants={staggerItem}>
          <AIInsightCard />
        </motion.div>

        {/* Universe status card */}
        <motion.div variants={staggerItem}>
          <UniverseStatusCard />
        </motion.div>

        <motion.div variants={staggerItem}>
          <OpenPositions />
        </motion.div>

        <motion.div
          className="grid grid-cols-2 gap-5"
          variants={staggerItemWithChildren(0.08)}
        >
          <motion.div variants={staggerItem}>
            <RecentTrades />
          </motion.div>
          <motion.div variants={staggerItem}>
            <HealthMini />
          </motion.div>
        </motion.div>
      </motion.div>

      {/* Watchlist overlay for tablet */}
      <WatchlistSidebar />
    </>
  );
}
