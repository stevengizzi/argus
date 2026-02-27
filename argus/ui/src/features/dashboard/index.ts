/**
 * Dashboard feature exports.
 *
 * Sprint 21d Session 4: Added OrchestratorStatusStrip.
 * RiskAllocationPanel kept for reference but no longer used on Dashboard
 * (migrated to Orchestrator page which imports CapitalAllocation directly).
 */

export { AccountSummary } from './AccountSummary';
export { DailyPnlCard } from './DailyPnlCard';
export { MarketStatusBadge } from './MarketStatusBadge';
export { OpenPositions } from './OpenPositions';
export { RecentTrades } from './RecentTrades';
export { HealthMini } from './HealthMini';
export { RiskAllocationPanel } from './RiskAllocationPanel';
export { SessionSummaryCard } from './SessionSummaryCard';
export { MarketRegimeCard } from './MarketRegimeCard';
export { OrchestratorStatusStrip } from './OrchestratorStatusStrip';

// Skeleton exports
export {
  AccountSummarySkeleton,
  DailyPnlSkeleton,
  MarketStatusSkeleton,
  OpenPositionsSkeleton,
  RecentTradesSkeleton,
  HealthMiniSkeleton,
} from './DashboardSkeleton';
