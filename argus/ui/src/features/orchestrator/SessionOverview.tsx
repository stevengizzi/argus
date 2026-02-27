/**
 * Session Overview card — aggregated session metrics.
 *
 * Displays summary data computed from all strategy allocations:
 * - Total P&L Today (prominent display)
 * - Trades Today
 * - Open Positions
 * - Active Strategies (count / total)
 * - Throttled Strategies (count or "None")
 */

import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { PnlValue } from '../../components/PnlValue';
import type { AllocationInfo } from '../../api/types';

interface SessionOverviewProps {
  allocations: AllocationInfo[];
}

export function SessionOverview({ allocations }: SessionOverviewProps) {
  // Aggregate metrics from all allocations
  const totalPnl = allocations.reduce((sum, a) => sum + a.daily_pnl, 0);
  const totalTrades = allocations.reduce((sum, a) => sum + a.trade_count_today, 0);
  const totalOpenPositions = allocations.reduce((sum, a) => sum + a.open_position_count, 0);
  const activeCount = allocations.filter((a) => a.is_active).length;
  const throttledCount = allocations.filter((a) => a.is_throttled).length;
  const totalStrategies = allocations.length;

  return (
    <Card>
      <CardHeader title="Session Overview" />
      <div className="space-y-4">
        {/* Total P&L - prominent display */}
        <div className="text-center py-2">
          <div className="text-xs text-argus-text-dim uppercase tracking-wide mb-1">
            Total P&L Today
          </div>
          <PnlValue value={totalPnl} size="xl" />
        </div>

        {/* Metric rows */}
        <div className="space-y-2 text-sm">
          <MetricRow label="Trades Today" value={totalTrades} />
          <MetricRow label="Open Positions" value={totalOpenPositions} />
          <MetricRow
            label="Active Strategies"
            value={`${activeCount} / ${totalStrategies}`}
          />
          <MetricRow
            label="Throttled"
            value={throttledCount === 0 ? 'None' : throttledCount}
            valueClassName={throttledCount === 0 ? 'text-argus-profit' : 'text-amber-400'}
          />
        </div>
      </div>
    </Card>
  );
}

interface MetricRowProps {
  label: string;
  value: string | number;
  valueClassName?: string;
}

function MetricRow({ label, value, valueClassName = 'text-argus-text' }: MetricRowProps) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-argus-text-dim">{label}</span>
      <span className={`font-medium tabular-nums ${valueClassName}`}>{value}</span>
    </div>
  );
}
