/**
 * Daily P&L card with large P&L display and trade count.
 *
 * Flashes on WebSocket updates when value changes.
 */

import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { LoadingState } from '../../components/LoadingState';
import { PnlValue } from '../../components/PnlValue';
import { useAccount } from '../../hooks/useAccount';

export function DailyPnlCard() {
  const { data, isLoading, error } = useAccount();

  if (isLoading) {
    return (
      <Card className="h-full">
        <CardHeader title="Daily P&L" />
        <LoadingState message="Loading..." />
      </Card>
    );
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

      {/* Large P&L number with flash animation */}
      <div className="flex items-baseline gap-2">
        <PnlValue value={data.daily_pnl} size="xl" flash />
      </div>

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
