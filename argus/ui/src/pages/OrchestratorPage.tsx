/**
 * Orchestrator page - operational nerve center.
 *
 * Shows real-time orchestrator status:
 * - RegimePanel: Session phase, market regime, indicator breakdown
 * - StrategyCoverageTimeline: Strategy operating windows visualization
 * - CapitalAllocation: Reused from dashboard (tracks donut/bars view)
 * - StrategyOperationsGrid: Per-strategy operational status cards
 * - DecisionTimeline: Today's orchestrator decisions in chronological order
 * - GlobalControls: Force rebalance, emergency flatten/pause buttons
 *
 * Uses stagger animation pattern from DashboardPage.
 */

import { motion } from 'framer-motion';
import { Gauge } from 'lucide-react';
import { AnimatedPage } from '../components/AnimatedPage';
import { Card } from '../components/Card';
import { CapitalAllocation } from '../components/CapitalAllocation';
import {
  RegimePanel,
  StrategyCoverageTimeline,
  StrategyOperationsGrid,
  DecisionTimeline,
  GlobalControls,
  ThrottleOverrideDialog,
  SessionOverview,
  OrchestratorSkeleton,
} from '../features/orchestrator';
import { useOrchestratorStatus } from '../hooks';
import { staggerContainer, staggerItem } from '../utils/motion';

export function OrchestratorPage() {
  const { data: orchestratorData, isLoading, error } = useOrchestratorStatus();

  // Extract allocation data for CapitalAllocation component
  const allocations = orchestratorData?.allocations.map(alloc => ({
    strategy_id: alloc.strategy_id,
    allocation_pct: alloc.allocation_pct,
    allocation_dollars: alloc.allocation_dollars,
    deployed_pct: alloc.deployed_pct,
    deployed_capital: alloc.deployed_capital,
    is_throttled: alloc.is_throttled,
  })) ?? [];

  if (isLoading) {
    return (
      <AnimatedPage>
        <div className="flex items-center gap-3 mb-6">
          <Gauge className="w-6 h-6 text-argus-accent" />
          <h1 className="text-xl font-semibold text-argus-text">Orchestrator</h1>
        </div>
        <OrchestratorSkeleton />
      </AnimatedPage>
    );
  }

  if (error) {
    return (
      <AnimatedPage>
        <div className="flex items-center gap-3 mb-6">
          <Gauge className="w-6 h-6 text-argus-accent" />
          <h1 className="text-xl font-semibold text-argus-text">Orchestrator</h1>
        </div>
        <Card>
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <p className="text-argus-warning mb-2">Unable to load orchestrator data</p>
            <p className="text-sm text-argus-text-dim">
              The orchestrator may be unavailable. Check system status.
            </p>
          </div>
        </Card>
      </AnimatedPage>
    );
  }

  return (
    <AnimatedPage>
      {/* Page header */}
      <div className="flex items-center gap-3 mb-6">
        <Gauge className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">Orchestrator</h1>
      </div>

      {/* Staggered content sections */}
      <motion.div
        className="space-y-6"
        variants={staggerContainer(0.08)}
        initial="hidden"
        animate="show"
      >
        {/* Section 1: Regime & Session */}
        <motion.div variants={staggerItem}>
          <RegimePanel orchestratorData={orchestratorData} />
        </motion.div>

        {/* Section 2: Strategy Coverage Timeline */}
        <motion.div variants={staggerItem}>
          <StrategyCoverageTimeline allocations={orchestratorData?.allocations ?? []} />
        </motion.div>

        {/* Section 3: Capital Allocation + Session Overview (side by side) */}
        <motion.div variants={staggerItem}>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <CapitalAllocation
              allocations={allocations}
              cashReservePct={orchestratorData?.cash_reserve_pct ?? 0.2}
              totalDeployedPct={orchestratorData?.total_deployed_pct}
              totalDeployedCapital={orchestratorData?.total_deployed_capital}
              totalEquity={orchestratorData?.total_equity}
            />
            <SessionOverview allocations={orchestratorData?.allocations ?? []} />
          </div>
        </motion.div>

        {/* Section 4: Strategy Operations */}
        <motion.div variants={staggerItem}>
          <StrategyOperationsGrid />
        </motion.div>

        {/* Section 5: Decision Timeline */}
        <motion.div variants={staggerItem}>
          <DecisionTimeline />
        </motion.div>

        {/* Section 6: Global Controls */}
        <motion.div variants={staggerItem}>
          <GlobalControls />
        </motion.div>
      </motion.div>

      {/* Throttle override dialog (mounted outside scroll flow) */}
      <ThrottleOverrideDialog />
    </AnimatedPage>
  );
}
