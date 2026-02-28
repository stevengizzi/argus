/**
 * System health and monitoring page.
 *
 * Shows overall system status, component health, intelligence placeholders,
 * and WebSocket event log. Infrastructure-focused — operations moved to Orchestrator.
 *
 * Sprint 21d — System cleanup (DEC-210).
 */

import { motion } from 'framer-motion';
import { Activity } from 'lucide-react';
import {
  SystemOverview,
  ComponentStatusList,
  EventsLog,
  IntelligencePlaceholders,
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

      {/* Main content grid: SystemOverview + ComponentStatusList */}
      <motion.div className="grid grid-cols-1 lg:grid-cols-2 gap-6" variants={staggerItem}>
        <SystemOverview />
        <ComponentStatusList />
      </motion.div>

      {/* Intelligence placeholders */}
      <motion.div variants={staggerItem}>
        <IntelligencePlaceholders />
      </motion.div>

      {/* Events log - full width at bottom */}
      <motion.div variants={staggerItem}>
        <EventsLog />
      </motion.div>
    </motion.div>
  );
}
