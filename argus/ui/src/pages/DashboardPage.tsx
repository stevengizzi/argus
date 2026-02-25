/**
 * Dashboard page - main command post view.
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
  RiskAllocationPanel,
  SessionSummaryCard,
} from '../features/dashboard';
import { WatchlistSidebar } from '../features/watchlist';
import { staggerContainer, staggerItem, staggerItemWithChildren } from '../utils/motion';
import { useIsMultiColumn, useMediaQuery } from '../hooks/useMediaQuery';

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
          {/* Session summary card - shows after market close with trades */}
          <SessionSummaryCard />
          <motion.div variants={staggerItem}><AccountSummary /></motion.div>
          <motion.div variants={staggerItem}><DailyPnlCard /></motion.div>

          {/* Market pair: always 2-col even on phone */}
          <motion.div
            className="grid grid-cols-2 gap-4"
            variants={staggerItem}
          >
            <MarketStatusBadge />
            <MarketRegimeCard />
          </motion.div>

          <RiskAllocationPanel />
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
          <SessionSummaryCard />

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
              <MarketStatusBadge />
            </motion.div>
          </motion.div>

          <RiskAllocationPanel />

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

        <motion.div
          className="grid grid-cols-2 gap-5"
          variants={staggerItem}
        >
          <MarketStatusBadge />
          <MarketRegimeCard />
        </motion.div>

        <RiskAllocationPanel />

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
