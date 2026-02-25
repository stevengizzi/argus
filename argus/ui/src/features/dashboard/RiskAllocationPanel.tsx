/**
 * Risk and Allocation panel for Dashboard.
 *
 * Combines CapitalAllocation (17-A, 18.75), RiskGauge (17-C), and MarketRegimeCard
 * with data fetching. Handles orchestrator unavailability gracefully (dev mode,
 * system starting).
 *
 * IMPORTANT: This component always renders the same DOM structure.
 * It never conditionally swaps between skeleton and content, because
 * doing so tears down child components (losing refs, replaying animations).
 * Children handle empty/loading states internally.
 *
 * Layout (Sprint 18.75 Fix A):
 * - Desktop/Tablet: 3-card equal-width grid (Capital, Risk, Regime)
 * - Mobile: All 3 cards stacked vertically, full width each
 */

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { CapitalAllocation } from '../../components/CapitalAllocation';
import { RiskGauge } from '../../components/RiskGauge';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { MarketRegimeCard } from './MarketRegimeCard';
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
  const { allocations, cashReservePct, totalDeployedPct, totalDeployedCapital, totalEquity } = useMemo(() => {
    const allocs = orchestratorData?.allocations.map(alloc => ({
      strategy_id: alloc.strategy_id,
      allocation_pct: alloc.allocation_pct,
      allocation_dollars: alloc.allocation_dollars,
      deployed_pct: alloc.deployed_pct,
      deployed_capital: alloc.deployed_capital,
      is_throttled: alloc.is_throttled,
    })) ?? [];
    const reserve = orchestratorData?.cash_reserve_pct ?? 0.2;
    return {
      allocations: allocs,
      cashReservePct: reserve,
      totalDeployedPct: orchestratorData?.total_deployed_pct,
      totalDeployedCapital: orchestratorData?.total_deployed_capital,
      totalEquity: orchestratorData?.total_equity,
    };
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
    // Desktop (lg+): 3-card equal-width grid (Capital, Risk, MarketRegime)
    // Tablet: 2-card grid (Capital, Risk) — MarketRegime shown in paired row above
    return (
      <motion.div
        className="grid grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 lg:gap-6"
        variants={staggerItem}
      >
        {/* Capital Allocation */}
        <CapitalAllocation
          allocations={allocations}
          cashReservePct={cashReservePct}
          totalDeployedPct={totalDeployedPct}
          totalDeployedCapital={totalDeployedCapital}
          totalEquity={totalEquity}
        />

        {/* Risk Budget */}
        <Card className="h-full">
          <CardHeader title="Risk Budget" />
          <div className="flex justify-around items-center py-4 min-h-[160px]">
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

        {/* Market Regime - visible only on desktop (lg+), hidden on tablet */}
        {/* On tablet, MarketRegime is shown paired with MarketStatus in DashboardPage */}
        <div className="hidden lg:block">
          <MarketRegimeCard />
        </div>
      </motion.div>
    );
  }

  // Mobile: stacked layout (Capital + Risk only)
  // MarketRegimeCard is shown in the paired row with MarketStatus in DashboardPage
  return (
    <>
      <motion.div variants={staggerItem}>
        <CapitalAllocation
          allocations={allocations}
          cashReservePct={cashReservePct}
          totalDeployedPct={totalDeployedPct}
          totalDeployedCapital={totalDeployedCapital}
          totalEquity={totalEquity}
        />
      </motion.div>

      <motion.div variants={staggerItem}>
        <Card>
          <CardHeader title="Risk Budget" />
          <div className="grid grid-cols-2 gap-4 py-4">
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
