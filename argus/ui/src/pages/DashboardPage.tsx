/**
 * Dashboard page - main command post view.
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
import {
  AccountSummary,
  DailyPnlCard,
  MarketStatusBadge,
  MarketRegimeCard,
  OpenPositions,
  RecentTrades,
  HealthMini,
  SessionSummaryCard,
  OrchestratorStatusStrip,
} from '../features/dashboard';
import { WatchlistSidebar } from '../features/watchlist';
import { staggerContainer, staggerItem, staggerItemWithChildren } from '../utils/motion';
import { useIsMultiColumn, useMediaQuery } from '../hooks/useMediaQuery';

/**
 * Placeholder for GoalTracker component (Session 5).
 */
function GoalTrackerPlaceholder() {
  return (
    <div className="bg-argus-surface border border-argus-border rounded-lg p-4 h-full flex items-center justify-center">
      <span className="text-sm text-argus-text-dim">Goal Tracker (Session 5)</span>
    </div>
  );
}

/**
 * Placeholder for HeatStripPortfolioBar component (Session 5).
 */
function HeatStripPlaceholder() {
  return (
    <div className="bg-argus-surface-2/30 border border-argus-border/50 rounded-lg px-4 py-2">
      <span className="text-xs text-argus-text-dim">Portfolio Heat Strip (Session 5)</span>
    </div>
  );
}

export function DashboardPage() {
  const isMultiColumn = useIsMultiColumn();
  const isDesktop = useMediaQuery('(min-width: 1024px)');

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

          {/* Heat strip placeholder */}
          <motion.div variants={staggerItem}>
            <HeatStripPlaceholder />
          </motion.div>

          {/* Session summary card - shows after market close with trades */}
          <SessionSummaryCard />

          <motion.div variants={staggerItem}><AccountSummary /></motion.div>
          <motion.div variants={staggerItem}><DailyPnlCard /></motion.div>
          <motion.div variants={staggerItem}><GoalTrackerPlaceholder /></motion.div>

          {/* Market pair: always 2-col even on phone */}
          <motion.div
            className="grid grid-cols-2 gap-4"
            variants={staggerItem}
          >
            <MarketStatusBadge />
            <MarketRegimeCard />
          </motion.div>

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

          {/* Heat strip placeholder */}
          <motion.div variants={staggerItem}>
            <HeatStripPlaceholder />
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
              <GoalTrackerPlaceholder />
            </motion.div>
          </motion.div>

          {/* 2-col row: Market Status | Market Regime */}
          <motion.div
            className="grid grid-cols-2 gap-6"
            variants={staggerItemWithChildren(0.08)}
          >
            <motion.div variants={staggerItem} className="h-full">
              <MarketStatusBadge />
            </motion.div>
            <motion.div variants={staggerItem} className="h-full">
              <MarketRegimeCard />
            </motion.div>
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

        {/* Heat strip placeholder */}
        <motion.div variants={staggerItem}>
          <HeatStripPlaceholder />
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

        {/* GoalTracker placeholder - full width on tablet */}
        <motion.div variants={staggerItem}>
          <GoalTrackerPlaceholder />
        </motion.div>

        <motion.div
          className="grid grid-cols-2 gap-5"
          variants={staggerItem}
        >
          <MarketStatusBadge />
          <MarketRegimeCard />
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
