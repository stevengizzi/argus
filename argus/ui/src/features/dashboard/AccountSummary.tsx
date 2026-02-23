/**
 * Account summary card showing equity, cash, and buying power.
 *
 * Hero equity number in large text with supporting metrics below.
 */

import { AnimatedNumber } from '../../components/AnimatedNumber';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { useAccount } from '../../hooks/useAccount';
import { formatCurrency } from '../../utils/format';
import { AccountSummarySkeleton } from './DashboardSkeleton';

export function AccountSummary() {
  const { data, isLoading, error } = useAccount();

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

      {/* Hero equity number with smooth count animation */}
      <AnimatedNumber
        value={data.equity}
        format={formatCurrency}
        className="text-3xl font-semibold text-argus-text"
      />

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
