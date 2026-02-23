/**
 * Daily P&L card with large P&L display and trade count.
 *
 * Flashes on WebSocket updates when value changes.
 */

import { AnimatedNumber } from '../../components/AnimatedNumber';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { PnlValue } from '../../components/PnlValue';
import { useAccount } from '../../hooks/useAccount';
import { formatCurrency } from '../../utils/format';
import { DailyPnlSkeleton } from './DashboardSkeleton';

/** Format P&L with sign for AnimatedNumber */
function formatPnlWithSign(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${formatCurrency(value)}`;
}

export function DailyPnlCard() {
  const { data, isLoading, error } = useAccount();

  if (isLoading) {
    return <DailyPnlSkeleton />;
  }

  if (error || !data) {
    return (
      <Card className="h-full">
        <CardHeader title="Daily P&L" />
        <div className="text-argus-loss text-sm">Failed to load</div>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader title="Daily P&L" />

      {/* Large P&L number with smooth count animation */}
      <AnimatedNumber
        value={data.daily_pnl}
        format={formatPnlWithSign}
        className={`text-3xl font-medium transition-colors duration-300 ${
          data.daily_pnl > 0
            ? 'text-argus-profit'
            : data.daily_pnl < 0
              ? 'text-argus-loss'
              : 'text-argus-text-dim'
        }`}
      />

      {/* Percentage below */}
      <div className="mt-1">
        <PnlValue value={data.daily_pnl_pct} format="percent" size="sm" />
      </div>

      {/* Trade count */}
      <div className="mt-3 text-sm text-argus-text-dim">
        {data.daily_trades_count} trade{data.daily_trades_count !== 1 ? 's' : ''} today
      </div>
    </Card>
  );
}
