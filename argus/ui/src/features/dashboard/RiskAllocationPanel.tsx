/**
 * Risk and Allocation panel for Dashboard.
 *
 * Combines AllocationDonut (17-A) and RiskGauge (17-C) with data fetching.
 * Handles orchestrator unavailability gracefully (dev mode, system starting).
 *
 * IMPORTANT: This component always renders the same DOM structure.
 * It never conditionally swaps between skeleton and content, because
 * doing so tears down child components (losing refs, replaying animations).
 * Children handle empty/loading states internally.
 *
 * Layout:
 * - Desktop: Donut and risk gauges in a horizontal row
 * - Tablet: Same row, slightly smaller
 * - Mobile: Donut full width, risk gauges in 2-column grid below
 */

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { AllocationDonut } from '../../components/AllocationDonut';
import { RiskGauge } from '../../components/RiskGauge';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { useOrchestratorStatus, usePerformance, useAccount } from '../../hooks';
import { staggerItem } from '../../utils/motion';
import { useIsMultiColumn } from '../../hooks/useMediaQuery';

// Risk limits from config/risk_limits.yaml (hardcoded for now, could come from API)
const DAILY_LOSS_LIMIT_PCT = 0.03; // 3%
const WEEKLY_LOSS_LIMIT_PCT = 0.05; // 5%

export function RiskAllocationPanel() {
  const isMultiColumn = useIsMultiColumn();
  const { data: orchestratorData } = useOrchestratorStatus();
  const { data: performanceData } = usePerformance('week');
  const { data: accountData } = useAccount();

  // Memoize allocation data to prevent unnecessary child re-renders
  const { allocations, cashReservePct } = useMemo(() => {
    const allocs = orchestratorData?.allocations.map(alloc => ({
      strategy_id: alloc.strategy_id,
      allocation_pct: alloc.allocation_pct,
      daily_pnl: 0,
    })) ?? [];
    const reserve = orchestratorData?.cash_reserve_pct ?? 0.2;
    return { allocations: allocs, cashReservePct: reserve };
  }, [orchestratorData]);

  // Memoize risk calculations
  const { dailyRiskConsumed, weeklyRiskConsumed } = useMemo(() => {
    const equity = accountData?.equity ?? 100000;
    const dailyLossLimit = equity * DAILY_LOSS_LIMIT_PCT;
    const weeklyLossLimit = equity * WEEKLY_LOSS_LIMIT_PCT;
    const dailyPnl = accountData?.daily_pnl ?? 0;
    const weeklyPnl = performanceData?.metrics.net_pnl ?? 0;
    return {
      dailyRiskConsumed: dailyPnl < 0
        ? Math.min(100, Math.abs(dailyPnl) / dailyLossLimit * 100)
        : 0,
      weeklyRiskConsumed: weeklyPnl < 0
        ? Math.min(100, Math.abs(weeklyPnl) / weeklyLossLimit * 100)
        : 0,
    };
  }, [accountData?.equity, accountData?.daily_pnl, performanceData?.metrics.net_pnl]);

  if (isMultiColumn) {
    // Desktop/Tablet: horizontal layout
    return (
      <motion.div
        className="grid grid-cols-3 gap-4 md:gap-5 lg:gap-6"
        variants={staggerItem}
      >
        {/* Allocation Donut */}
        <div className="col-span-1">
          <AllocationDonut
            allocations={allocations}
            cashReservePct={cashReservePct}
          />
        </div>

        {/* Risk Gauges */}
        <div className="col-span-2">
          <Card className="h-full">
            <CardHeader title="Risk Budget" />
            <div className="flex justify-around items-center h-full pt-2">
              <RiskGauge
                label="Daily Risk"
                value={dailyRiskConsumed}
                maxLabel={`${(DAILY_LOSS_LIMIT_PCT * 100).toFixed(0)}% limit`}
                size="md"
              />
              <RiskGauge
                label="Weekly Risk"
                value={weeklyRiskConsumed}
                maxLabel={`${(WEEKLY_LOSS_LIMIT_PCT * 100).toFixed(0)}% limit`}
                size="md"
              />
            </div>
          </Card>
        </div>
      </motion.div>
    );
  }

  // Mobile: stacked layout
  return (
    <>
      <motion.div variants={staggerItem}>
        <AllocationDonut
          allocations={allocations}
          cashReservePct={cashReservePct}
        />
      </motion.div>

      <motion.div variants={staggerItem}>
        <Card>
          <CardHeader title="Risk Budget" />
          <div className="grid grid-cols-2 gap-4 pt-2">
            <RiskGauge
              label="Daily Risk"
              value={dailyRiskConsumed}
              maxLabel={`${(DAILY_LOSS_LIMIT_PCT * 100).toFixed(0)}% limit`}
              size="sm"
            />
            <RiskGauge
              label="Weekly Risk"
              value={weeklyRiskConsumed}
              maxLabel={`${(WEEKLY_LOSS_LIMIT_PCT * 100).toFixed(0)}% limit`}
              size="sm"
            />
          </div>
        </Card>
      </motion.div>
    </>
  );
}
