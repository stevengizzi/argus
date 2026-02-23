/**
 * Daily P&L card with large P&L display, trend sparkline, and trade count.
 *
 * Flashes on WebSocket updates when value changes.
 */

import { AnimatedNumber } from '../../components/AnimatedNumber';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { PnlValue } from '../../components/PnlValue';
import { Sparkline } from '../../components/Sparkline';
import { useAccount } from '../../hooks/useAccount';
import { useLiveEquity } from '../../hooks/useLiveEquity';
import { useSparklineData } from '../../hooks/useSparklineData';
import { formatCurrency } from '../../utils/format';
import { DailyPnlSkeleton } from './DashboardSkeleton';

/** Format P&L with sign for AnimatedNumber */
function formatPnlWithSign(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${formatCurrency(value)}`;
}

export function DailyPnlCard() {
  const { data, isLoading, error } = useAccount();
  const { pnlTrend } = useSparklineData();
  const liveEquity = useLiveEquity();

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

  // Use live values when available, fall back to REST
  const dailyPnl = liveEquity?.dailyPnl ?? data.daily_pnl;
  const dailyPnlPct = liveEquity?.dailyPnlPct ?? data.daily_pnl_pct;

  // Determine sparkline color based on today's P&L (updates in real-time)
  const sparklineColor =
    dailyPnl > 0
      ? 'var(--color-argus-profit)'
      : dailyPnl < 0
        ? 'var(--color-argus-loss)'
        : 'var(--color-argus-text-dim)';

  return (
    <Card className="h-full">
      <CardHeader title="Daily P&L" />

      {/* Large P&L number with smooth count animation — uses live WS data when available */}
      <AnimatedNumber
        value={dailyPnl}
        format={formatPnlWithSign}
        className={`text-3xl font-medium transition-colors duration-300 ${
          dailyPnl > 0
            ? 'text-argus-profit'
            : dailyPnl < 0
              ? 'text-argus-loss'
              : 'text-argus-text-dim'
        }`}
      />

      {/* Recent daily P&L sparkline — auto-measures container width */}
      {pnlTrend.length > 1 && (
        <div className="mt-2">
          <Sparkline
            data={pnlTrend}
            height={32}
            color={sparklineColor}
            fillOpacity={0.15}
          />
        </div>
      )}

      {/* Percentage below — uses live WS data when available */}
      <div className="mt-1">
        <PnlValue value={dailyPnlPct} format="percent" size="sm" />
      </div>

      {/* Trade count */}
      <div className="mt-3 text-sm text-argus-text-dim">
        {data.daily_trades_count} trade{data.daily_trades_count !== 1 ? 's' : ''} today
      </div>
    </Card>
  );
}
