/**
 * System health and monitoring page.
 *
 * Shows overall system status, component health, strategy cards,
 * and WebSocket event log.
 */

import { motion } from 'framer-motion';
import { Activity } from 'lucide-react';
import {
  SystemOverview,
  ComponentStatusList,
  StrategyCards,
  EventsLog,
  EmergencyControls,
} from '../features/system';
import { staggerContainer, staggerItem } from '../utils/motion';

export function SystemPage() {
  return (
    <motion.div
      className="space-y-6"
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      {/* Page header */}
      <motion.div className="flex items-center gap-3" variants={staggerItem}>
        <Activity className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">System</h1>
      </motion.div>

      {/* Main content grid */}
      <motion.div className="grid grid-cols-1 lg:grid-cols-2 gap-6" variants={staggerItem}>
        {/* Left column: Overview and Components */}
        <div className="space-y-6">
          <SystemOverview />
          <ComponentStatusList />
        </div>

        {/* Right column: Strategies */}
        <div>
          <StrategyCards />
        </div>
      </motion.div>

      {/* Events log - full width at bottom */}
      <motion.div variants={staggerItem}>
        <EventsLog />
      </motion.div>

      {/* Emergency controls */}
      <motion.div variants={staggerItem}>
        <EmergencyControls />
      </motion.div>
    </motion.div>
  );
}
