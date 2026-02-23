/**
 * Dashboard page - main command post view.
 *
 * Responsive grid layout with three breakpoints:
 * - Phone (<640px): Single column stacked layout with flat vertical stagger
 * - Tablet (640-1023px): Two-column grid with grouped stagger
 * - Desktop (>=1024px): Full three-column layout with grouped stagger
 *
 * Stagger animation is responsive:
 * - Multi-column (tablet+): Cards in a row stagger left-to-right within grid groups
 * - Single column (phone): All cards as direct children, stagger top-to-bottom linearly
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
import { useIsMultiColumn } from '../hooks/useMediaQuery';

export function DashboardPage() {
  const isMultiColumn = useIsMultiColumn();

  if (!isMultiColumn) {
    // Phone: flat vertical stagger, all cards as direct children
    // Key forces clean remount when crossing responsive threshold to reset animation states
    return (
      <motion.div
        key="dashboard-single"
        className="space-y-4"
        variants={staggerContainer(0.08)}
        initial="hidden"
        animate="show"
      >
        <motion.div variants={staggerItem}><AccountSummary /></motion.div>
        <motion.div variants={staggerItem}><DailyPnlCard /></motion.div>
        <motion.div variants={staggerItem}><MarketStatusBadge /></motion.div>
        <motion.div variants={staggerItem}><OpenPositions /></motion.div>
        <motion.div variants={staggerItem}><RecentTrades /></motion.div>
        <motion.div variants={staggerItem}><HealthMini /></motion.div>
      </motion.div>
    );
  }

  // Tablet/Desktop: grid layout with grouped stagger
  // Key forces clean remount when crossing responsive threshold to reset animation states
  return (
    <motion.div
      key="dashboard-multi"
      className="space-y-4 md:space-y-5 lg:space-y-6"
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      {/* Top row: 2-col tablet, 3-col desktop */}
      <motion.div
        className="grid grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 lg:gap-6"
        variants={staggerItemWithChildren(0.08)}
      >
        <motion.div variants={staggerItem} className="h-full">
          <AccountSummary />
        </motion.div>
        <motion.div variants={staggerItem} className="h-full">
          <DailyPnlCard />
        </motion.div>
        <motion.div variants={staggerItem} className="md:col-span-2 lg:col-span-1 h-full">
          <MarketStatusBadge />
        </motion.div>
      </motion.div>

      {/* Open positions - full width */}
      <motion.div variants={staggerItem}>
        <OpenPositions />
      </motion.div>

      {/* Bottom row: 2-col */}
      <motion.div
        className="grid grid-cols-2 gap-4 md:gap-5 lg:gap-6"
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
