/**
 * Account summary card showing equity, cash, and buying power.
 *
 * Hero equity number in large text with supporting metrics below.
 */

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

      {/* Hero equity number */}
      <div className="text-3xl font-semibold tabular-nums text-argus-text">
        {formatCurrency(data.equity)}
      </div>

      {/* Supporting metrics */}
      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-argus-text-dim">Cash</span>
          <div className="tabular-nums text-argus-text">{formatCurrency(data.cash)}</div>
        </div>
        <div>
          <span className="text-argus-text-dim">Buying Power</span>
          <div className="tabular-nums text-argus-text">{formatCurrency(data.buying_power)}</div>
        </div>
      </div>
    </Card>
  );
}
