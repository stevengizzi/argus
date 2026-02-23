/**
 * Dashboard page - main command post view.
 *
 * Responsive grid layout with three breakpoints:
 * - Phone (<640px): Single column stacked layout
 * - Tablet (640-1023px): Two-column grid
 * - Desktop (>=1024px): Full three-column layout
 *
 * Stagger animation is responsive:
 * - Multi-column (tablet+): Cards in a row stagger left-to-right
 * - Single column (phone): All cards stagger top-to-bottom linearly
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
import { staggerContainer, staggerItem, staggerItemResponsive } from '../utils/motion';
import { useIsMultiColumn } from '../hooks/useMediaQuery';

export function DashboardPage() {
  const isMultiColumn = useIsMultiColumn();

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
      {/* Grid uses responsive stagger: L-to-R on tablet+, linear on phone */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 lg:gap-6"
        variants={staggerItemResponsive(isMultiColumn, 0.08)}
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
      {/* Grid uses responsive stagger: L-to-R on tablet+, linear on phone */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5 lg:gap-6"
        variants={staggerItemResponsive(isMultiColumn, 0.08)}
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
