/**
 * Recent trades list showing the last 8 trades.
 *
 * Compact format with symbol, P&L, exit reason badge, and time.
 * Links to full trade log at bottom.
 */

import { Link } from 'react-router-dom';
import { ScrollText, ArrowRight } from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { LoadingState } from '../../components/LoadingState';
import { EmptyState } from '../../components/EmptyState';
import { PnlValue } from '../../components/PnlValue';
import { Badge } from '../../components/Badge';
import { useTrades } from '../../hooks/useTrades';
import { formatTime } from '../../utils/format';

type ExitReason = 'target_1' | 'target_2' | 'stop_loss' | 'time_stop' | 'eod' | string;

const exitReasonLabels: Record<string, string> = {
  target_1: 'T1',
  target_2: 'T2',
  stop_loss: 'SL',
  time_stop: 'TIME',
  eod: 'EOD',
};

const exitReasonVariants: Record<string, 'success' | 'danger' | 'warning' | 'neutral'> = {
  target_1: 'success',
  target_2: 'success',
  stop_loss: 'danger',
  time_stop: 'warning',
  eod: 'neutral',
};

function getExitReasonLabel(reason: ExitReason): string {
  return exitReasonLabels[reason] ?? reason.toUpperCase();
}

function getExitReasonVariant(reason: ExitReason): 'success' | 'danger' | 'warning' | 'neutral' {
  return exitReasonVariants[reason] ?? 'neutral';
}

export function RecentTrades() {
  const { data, isLoading, error } = useTrades({ limit: 8 });

  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Recent Trades" />
        <LoadingState message="Loading trades..." />
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader title="Recent Trades" />
        <div className="text-argus-loss text-sm">Failed to load trades</div>
      </Card>
    );
  }

  const trades = data?.trades ?? [];

  if (trades.length === 0) {
    return (
      <Card>
        <CardHeader title="Recent Trades" />
        <EmptyState icon={ScrollText} message="No trades yet" />
      </Card>
    );
  }

  return (
    <Card noPadding>
      <div className="p-4 pb-0">
        <CardHeader title="Recent Trades" subtitle={`Last ${trades.length}`} />
      </div>

      {/* Trade list */}
      <div className="divide-y divide-argus-border">
        {trades.map((trade) => (
          <div
            key={trade.id}
            className="px-4 py-2.5 flex items-center justify-between hover:bg-argus-bg/50"
          >
            {/* Left: Symbol and P&L */}
            <div className="flex items-center gap-3">
              <span className="font-medium text-argus-text w-12">{trade.symbol}</span>
              <PnlValue value={trade.pnl_dollars ?? 0} size="sm" />
            </div>

            {/* Right: Exit reason and time */}
            <div className="flex items-center gap-3">
              {trade.exit_reason && (
                <Badge variant={getExitReasonVariant(trade.exit_reason)}>
                  {getExitReasonLabel(trade.exit_reason)}
                </Badge>
              )}
              <span className="text-xs text-argus-text-dim tabular-nums w-20 text-right">
                {trade.exit_time ? formatTime(trade.exit_time) : '—'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Link to full trade log */}
      <div className="p-4 pt-2 border-t border-argus-border">
        <Link
          to="/trades"
          className="flex items-center gap-1 text-sm text-argus-accent hover:underline"
        >
          View all trades
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </Card>
  );
}
