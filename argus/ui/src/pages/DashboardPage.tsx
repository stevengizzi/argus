/**
 * Dashboard page - main command post view.
 *
 * Responsive grid layout with three breakpoints:
 * - Phone (<640px): Single column stacked layout
 * - Tablet (640-1023px): Two-column grid
 * - Desktop (>=1024px): Full three-column layout
 */

import { motion } from 'framer-motion';
import {
  AccountSummary,
  DailyPnlCard,
  MarketStatusBadge,
  OpenPositions,
  RecentTrades,
  HealthMini,
} from '../features/dashboard';
import { staggerContainer, staggerItem, staggerItemWithChildren } from '../utils/motion';

export function DashboardPage() {
  return (
    <motion.div
      className="space-y-4 md:space-y-5 lg:space-y-6"
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      {/* Top row: Account, Daily P&L, Market Status */}
      {/* Phone: Stack vertically */}
      {/* Tablet: 2 columns with Market spanning full width below */}
      {/* Desktop: 3 equal columns */}
      {/* Grid uses staggerItemWithChildren: sequences with page siblings AND staggers its cards L-to-R */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 lg:gap-6"
        variants={staggerItemWithChildren(0.08)}
      >
        <motion.div variants={staggerItem} className="h-full">
          <AccountSummary />
        </motion.div>
        <motion.div variants={staggerItem} className="h-full">
          <DailyPnlCard />
        </motion.div>
        {/* On tablet, market badge spans full width in its own row */}
        <motion.div variants={staggerItem} className="md:col-span-2 lg:col-span-1 h-full">
          <MarketStatusBadge />
        </motion.div>
      </motion.div>

      {/* Open positions - full width */}
      <motion.div variants={staggerItem}>
        <OpenPositions />
      </motion.div>

      {/* Bottom row: Recent Trades and Health Status */}
      {/* Phone: Stack vertically */}
      {/* Tablet: 2 columns */}
      {/* Desktop: 2 columns */}
      {/* Grid uses staggerItemWithChildren: sequences with page siblings AND staggers its cards L-to-R */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5 lg:gap-6"
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
  );
}
