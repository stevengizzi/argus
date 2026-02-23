/**
 * Recent trades list showing the last 8 trades.
 *
 * Compact format with symbol, P&L, exit reason badge, and time.
 * Links to full trade log at bottom.
 * New trades slide in with animation on WebSocket updates.
 */

import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { BarChart3, ArrowRight } from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { EmptyState } from '../../components/EmptyState';
import { PnlValue } from '../../components/PnlValue';
import { Badge } from '../../components/Badge';
import { useTrades } from '../../hooks/useTrades';
import { formatTime } from '../../utils/format';
import { RecentTradesSkeleton } from './DashboardSkeleton';
import { isPreMarket } from '../../utils/marketTime';
import { shouldShowEmpty } from '../../utils/testMode';
import { DURATION, EASE } from '../../utils/motion';

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

// Animation variants for trade list items
const tradeItemVariants = {
  initial: { opacity: 0, y: -8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.normal, ease: EASE.out },
  },
  exit: {
    opacity: 0,
    transition: { duration: DURATION.fast },
  },
};

export function RecentTrades() {
  const { data, isLoading, error } = useTrades({ limit: 8 });

  // Memoize trades array to avoid dependency issues
  const trades = useMemo(() => data?.trades ?? [], [data?.trades]);

  if (isLoading) {
    return <RecentTradesSkeleton />;
  }

  if (error) {
    return (
      <Card>
        <CardHeader title="Recent Trades" />
        <div className="text-argus-loss text-sm">Failed to load trades</div>
      </Card>
    );
  }

  // Test mode: force empty state for testing
  const forceEmpty = shouldShowEmpty('trades');

  if (trades.length === 0 || forceEmpty) {
    // Contextual empty state based on market time
    const preMarket = isPreMarket();
    const message = preMarket
      ? 'No trades today — first signal expected after 9:35 AM ET'
      : 'No trades today';

    return (
      <Card>
        <CardHeader title="Recent Trades" />
        <EmptyState icon={BarChart3} message={message} />
      </Card>
    );
  }

  return (
    <Card noPadding>
      <div className="p-4 pb-0">
        <CardHeader title="Recent Trades" subtitle={`Last ${trades.length}`} />
      </div>

      {/* Trade list with slide-in animation */}
      <div className="divide-y divide-argus-border">
        <AnimatePresence initial={false} mode="popLayout">
          {trades.map((trade) => (
            <motion.div
              key={trade.id}
              layout
              layoutId={trade.id}
              variants={tradeItemVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              className="px-4 py-2.5 flex items-center justify-between hover:bg-argus-bg/50 transition-colors duration-150"
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
            </motion.div>
          ))}
        </AnimatePresence>
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
