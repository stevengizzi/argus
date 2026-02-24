/**
 * Session Summary Card - Post-market debrief card.
 *
 * Shows when market is closed (after 16:00 ET) and there are trades today.
 * Dismissable via local state. Shows net P&L, trade count, wins/losses,
 * best/worst trades, strategy badges, and regime badge.
 *
 * Implements 18-D from UX_FEATURE_BACKLOG.md.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { Card } from '../../components/Card';
import { StrategyBadge, RegimeBadge } from '../../components/Badge';
import { useSessionSummary } from '../../hooks';
import { getMarketContext } from '../../utils/marketTime';
import { formatCurrency, formatR } from '../../utils/format';
import { staggerContainer, staggerItem, DURATION, EASE } from '../../utils/motion';

// Skeleton for loading state
function SessionSummarySkeleton() {
  return (
    <Card className="relative">
      <div className="animate-pulse">
        <div className="flex items-center justify-between mb-4">
          <div className="h-5 w-32 bg-argus-surface-2 rounded" />
          <div className="h-5 w-5 bg-argus-surface-2 rounded" />
        </div>
        <div className="h-10 w-40 bg-argus-surface-2 rounded mb-4" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 w-16 bg-argus-surface-2 rounded" />
              <div className="h-6 w-20 bg-argus-surface-2 rounded" />
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// Individual stat item
interface StatItemProps {
  label: string;
  value: string;
  colorClass?: string;
}

function StatItem({ label, value, colorClass = 'text-argus-text' }: StatItemProps) {
  return (
    <motion.div variants={staggerItem} className="space-y-1">
      <div className="text-xs text-argus-text-dim uppercase tracking-wider">{label}</div>
      <div className={`text-lg font-medium ${colorClass}`}>{value}</div>
    </motion.div>
  );
}

export function SessionSummaryCard() {
  const [dismissed, setDismissed] = useState(false);
  const { data, isLoading, error } = useSessionSummary();
  const marketContext = getMarketContext();

  // Don't show if dismissed
  if (dismissed) {
    return null;
  }

  // Only show after market close (after_hours or closed)
  const showCard = marketContext.status === 'after_hours' || marketContext.status === 'closed';
  if (!showCard) {
    return null;
  }

  // Show skeleton while loading
  if (isLoading) {
    return <SessionSummarySkeleton />;
  }

  // Don't show if error or no data
  if (error || !data) {
    return null;
  }

  // Don't show if no trades today
  if (data.trade_count === 0) {
    return null;
  }

  const pnlColorClass =
    data.net_pnl > 0
      ? 'text-argus-profit'
      : data.net_pnl < 0
        ? 'text-argus-loss'
        : 'text-argus-text-dim';

  const pnlSign = data.net_pnl >= 0 ? '+' : '';

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: DURATION.normal, ease: EASE.out }}
      >
        <Card className="relative">
          {/* Header with dismiss button */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium uppercase tracking-wider text-argus-text-dim">
              Session Summary
            </h3>
            <button
              onClick={() => setDismissed(true)}
              className="p-1 rounded hover:bg-argus-surface-2 text-argus-text-dim hover:text-argus-text transition-colors"
              aria-label="Dismiss session summary"
            >
              <X size={18} />
            </button>
          </div>

          {/* Large P&L display */}
          <div className={`text-4xl font-medium mb-6 ${pnlColorClass}`}>
            {pnlSign}{formatCurrency(data.net_pnl)}
          </div>

          {/* Stats grid */}
          <motion.div
            className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6"
            variants={staggerContainer(0.06)}
            initial="hidden"
            animate="show"
          >
            <StatItem label="Trades" value={String(data.trade_count)} />
            <StatItem
              label="Win/Loss"
              value={`${data.wins}W / ${data.losses}L`}
              colorClass={data.wins > data.losses ? 'text-argus-profit' : data.wins < data.losses ? 'text-argus-loss' : 'text-argus-text'}
            />
            {data.best_trade && (
              <StatItem
                label="Best Trade"
                value={`${data.best_trade.symbol} ${formatR(data.best_trade.r_multiple).text}`}
                colorClass="text-argus-profit"
              />
            )}
            {data.worst_trade && (
              <StatItem
                label="Worst Trade"
                value={`${data.worst_trade.symbol} ${formatR(data.worst_trade.r_multiple).text}`}
                colorClass="text-argus-loss"
              />
            )}
          </motion.div>

          {/* Strategy badges and regime */}
          <div className="flex flex-wrap items-center gap-2">
            {data.active_strategies.length > 0 && (
              <>
                <span className="text-xs text-argus-text-dim">Strategies:</span>
                {data.active_strategies.map((strategyId) => (
                  <StrategyBadge key={strategyId} strategyId={strategyId} />
                ))}
              </>
            )}
            {data.regime && (
              <>
                <span className="text-xs text-argus-text-dim ml-2">Regime:</span>
                <RegimeBadge regime={data.regime} />
              </>
            )}
          </div>

          {/* Fill rate (if less than 100%) */}
          {data.fill_rate < 1.0 && (
            <div className="mt-3 text-xs text-argus-text-dim">
              Fill rate: {Math.round(data.fill_rate * 100)}%
            </div>
          )}
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}
