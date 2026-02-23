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
import { staggerContainer, staggerItem } from '../utils/motion';

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
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 lg:gap-6"
        variants={staggerItem}
      >
        {/* Inner stagger for summary cards with tighter delay */}
        <motion.div variants={staggerContainer(0.05)} initial="hidden" animate="show">
          <motion.div variants={staggerItem}>
            <AccountSummary />
          </motion.div>
        </motion.div>
        <motion.div variants={staggerContainer(0.05)} initial="hidden" animate="show">
          <motion.div variants={staggerItem}>
            <DailyPnlCard />
          </motion.div>
        </motion.div>
        {/* On tablet, market badge spans full width in its own row */}
        <motion.div
          className="md:col-span-2 lg:col-span-1 h-full"
          variants={staggerContainer(0.05)}
          initial="hidden"
          animate="show"
        >
          <motion.div variants={staggerItem}>
            <MarketStatusBadge />
          </motion.div>
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
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5 lg:gap-6"
        variants={staggerItem}
      >
        <RecentTrades />
        <HealthMini />
      </motion.div>
    </motion.div>
  );
}
