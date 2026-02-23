/**
 * Trade log page with filtering and pagination.
 *
 * Full trade history with strategy/outcome/date filters, summary stats, and paginated table.
 */

import { motion } from 'framer-motion';
import { ScrollText } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { TradeFilters, TradeStatsBar, TradeTable, TradeStatsBarSkeleton, TradeTableSkeleton } from '../features/trades';
import { useTrades } from '../hooks/useTrades';
import { staggerContainer, staggerItem } from '../utils/motion';

const ITEMS_PER_PAGE = 20;

export function TradesPage() {
  const [searchParams] = useSearchParams();

  // Read filter values from URL
  const strategy_id = searchParams.get('strategy') || undefined;
  const outcomeParam = searchParams.get('outcome');
  const outcome =
    outcomeParam === 'win' || outcomeParam === 'loss' || outcomeParam === 'breakeven'
      ? outcomeParam
      : undefined;
  const date_from = searchParams.get('from') || undefined;
  const date_to = searchParams.get('to') || undefined;
  const currentPage = parseInt(searchParams.get('page') || '1', 10);

  // Fetch trades with current filters
  const { data, isLoading, error } = useTrades({
    strategy_id,
    outcome,
    date_from,
    date_to,
    limit: ITEMS_PER_PAGE,
    offset: (currentPage - 1) * ITEMS_PER_PAGE,
  });

  return (
    <motion.div
      className="space-y-4 md:space-y-6"
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      {/* Page header */}
      <motion.div className="flex items-center gap-3" variants={staggerItem}>
        <ScrollText className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">Trades</h1>
      </motion.div>

      {/* Filters */}
      <motion.div variants={staggerItem}>
        <TradeFilters />
      </motion.div>

      {/* Stats bar */}
      <motion.div variants={staggerItem}>
        {isLoading ? (
          <TradeStatsBarSkeleton />
        ) : data ? (
          <TradeStatsBar trades={data.trades} totalCount={data.total_count} />
        ) : null}
      </motion.div>

      {/* Content area */}
      <motion.div variants={staggerItem}>
        {isLoading ? (
          <TradeTableSkeleton />
        ) : error ? (
          <div className="bg-argus-surface border border-argus-border rounded-lg p-8 text-center">
            <p className="text-argus-loss">Error loading trades: {error.message}</p>
          </div>
        ) : data ? (
          <TradeTable
            trades={data.trades}
            totalCount={data.total_count}
            limit={data.limit}
            isLoading={isLoading}
          />
        ) : null}
      </motion.div>
    </motion.div>
  );
}
