/**
 * Account summary card showing equity, cash, and buying power.
 *
 * Hero equity number in large text with 30-day equity trend sparkline.
 */

import { AnimatedNumber } from '../../components/AnimatedNumber';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { Sparkline } from '../../components/Sparkline';
import { useAccount } from '../../hooks/useAccount';
import { useLiveEquity } from '../../hooks/useLiveEquity';
import { useSparklineData } from '../../hooks/useSparklineData';
import { formatCurrency } from '../../utils/format';
import { AccountSummarySkeleton } from './DashboardSkeleton';

export function AccountSummary() {
  const { data, isLoading, error } = useAccount();
  const { equityTrend } = useSparklineData();
  const liveEquity = useLiveEquity();

  if (isLoading) {
    return <AccountSummarySkeleton />;
  }

  if (error || !data) {
    return (
      <Card className="h-full">
        <CardHeader title="Account" />
        <div className="text-argus-loss text-sm">Failed to load account data</div>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader title="Account Equity" />

      {/* Hero equity number with smooth count animation — uses live WS data when available */}
      <AnimatedNumber
        value={liveEquity?.equity ?? data.equity}
        format={formatCurrency}
        className="text-3xl font-semibold text-argus-text"
      />

      {/* 30-day equity trend sparkline — auto-measures container width */}
      {equityTrend.length > 1 && (
        <div className="mt-2">
          <Sparkline
            data={equityTrend}
            height={32}
            color="var(--color-argus-accent)"
            fillOpacity={0.15}
          />
        </div>
      )}

      {/* Supporting metrics with faster animations */}
      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-argus-text-dim">Cash</span>
          <AnimatedNumber
            value={data.cash}
            format={formatCurrency}
            duration={200}
            className="block text-argus-text"
          />
        </div>
        <div>
          <span className="text-argus-text-dim">Buying Power</span>
          <AnimatedNumber
            value={data.buying_power}
            format={formatCurrency}
            duration={200}
            className="block text-argus-text"
          />
        </div>
      </div>
    </Card>
  );
}
