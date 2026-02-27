/**
 * Orchestrator page - operational nerve center.
 *
 * Shows real-time orchestrator status:
 * - RegimePanel: Session phase, market regime, indicator breakdown
 * - StrategyCoverageTimeline: Strategy operating windows visualization
 * - CapitalAllocation: Reused from dashboard (tracks donut/bars view)
 * - Placeholder sections for Session 6-7 components
 *
 * Uses stagger animation pattern from DashboardPage.
 */

import { motion } from 'framer-motion';
import { Gauge } from 'lucide-react';
import { AnimatedPage } from '../components/AnimatedPage';
import { Card } from '../components/Card';
import { CardHeader } from '../components/CardHeader';
import { Skeleton } from '../components/Skeleton';
import { CapitalAllocation } from '../components/CapitalAllocation';
import { RegimePanel, StrategyCoverageTimeline } from '../features/orchestrator';
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
        <div className="space-y-6">
          <Card>
            <Skeleton className="h-24" />
          </Card>
          <Card>
            <Skeleton className="h-40" />
          </Card>
          <Card>
            <Skeleton className="h-64" />
          </Card>
        </div>
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

        {/* Section 3: Capital Allocation (reuse existing) */}
        <motion.div variants={staggerItem}>
          <CapitalAllocation
            allocations={allocations}
            cashReservePct={orchestratorData?.cash_reserve_pct ?? 0.2}
            totalDeployedPct={orchestratorData?.total_deployed_pct}
            totalDeployedCapital={orchestratorData?.total_deployed_capital}
            totalEquity={orchestratorData?.total_equity}
          />
        </motion.div>

        {/* Section 4: Strategy Operations — placeholder for Session 6 */}
        <motion.div variants={staggerItem}>
          <Card>
            <CardHeader title="Strategy Operations" subtitle="Session 6" />
            <div className="flex items-center justify-center h-32 text-sm text-argus-text-dim">
              Per-strategy cards with controls — coming in Session 6
            </div>
          </Card>
        </motion.div>

        {/* Section 5: Decision Timeline — placeholder for Session 7 */}
        <motion.div variants={staggerItem}>
          <Card>
            <CardHeader title="Decision Timeline" subtitle="Session 7" />
            <div className="flex items-center justify-center h-32 text-sm text-argus-text-dim">
              Today's orchestrator decisions — coming in Session 7
            </div>
          </Card>
        </motion.div>

        {/* Section 6: Global Controls — placeholder for Session 7 */}
        <motion.div variants={staggerItem}>
          <Card>
            <CardHeader title="Global Controls" subtitle="Session 7" />
            <div className="flex items-center justify-center h-20 text-sm text-argus-text-dim">
              Force rebalance, emergency controls — coming in Session 7
            </div>
          </Card>
        </motion.div>
      </motion.div>
    </AnimatedPage>
  );
}
