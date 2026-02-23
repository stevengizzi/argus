/**
 * Trade log page with filtering and pagination.
 *
 * Full trade history with strategy/outcome/date filters, summary stats, and paginated table.
 *
 * Uses local state for filters to prevent data flash during page exit animations.
 * Containers and headers persist during filter changes - only data values transition.
 */

import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { ScrollText } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import {
  TradeFilters,
  TradeStatsBar,
  TradeTable,
  TradeStatsBarSkeleton,
  TradeTableSkeleton,
} from '../features/trades';
import { useTrades } from '../hooks/useTrades';
import { staggerContainer, staggerItem } from '../utils/motion';
import type { OutcomeFilter, TradeFilterValues } from '../hooks/useTradeFilters';

const ITEMS_PER_PAGE = 20;

interface FilterState {
  strategy_id: string | undefined;
  outcome: OutcomeFilter;
  date_from: string | undefined;
  date_to: string | undefined;
  page: number;
}

export function TradesPage() {
  const [, setSearchParams] = useSearchParams();

  // Local state initialized from URL - immune to URL changes during exit animation
  const [filters, setFilters] = useState<FilterState>(() => {
    const params = new URLSearchParams(window.location.search);
    const outcomeParam = params.get('outcome');
    return {
      strategy_id: params.get('strategy') || undefined,
      outcome:
        outcomeParam === 'win' || outcomeParam === 'loss' || outcomeParam === 'breakeven'
          ? outcomeParam
          : 'all',
      date_from: params.get('from') || undefined,
      date_to: params.get('to') || undefined,
      page: parseInt(params.get('page') || '1', 10),
    };
  });

  // Update both local state and URL
  const updateFilters = useCallback(
    (updates: Partial<TradeFilterValues>) => {
      setFilters((prev) => {
        const next = { ...prev, ...updates };
        // Reset page on filter change (unless page itself is being updated)
        if (!('page' in updates)) {
          next.page = 1;
        }
        return next;
      });

      // Sync to URL for bookmarking
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);

          if (updates.strategy_id !== undefined) {
            if (updates.strategy_id) {
              next.set('strategy', updates.strategy_id);
            } else {
              next.delete('strategy');
            }
          }

          if (updates.outcome !== undefined) {
            if (updates.outcome === 'all') {
              next.delete('outcome');
            } else {
              next.set('outcome', updates.outcome);
            }
          }

          if (updates.date_from !== undefined) {
            if (updates.date_from) {
              next.set('from', updates.date_from);
            } else {
              next.delete('from');
            }
          }

          if (updates.date_to !== undefined) {
            if (updates.date_to) {
              next.set('to', updates.date_to);
            } else {
              next.delete('to');
            }
          }

          // Reset page on filter change
          if (!('page' in updates)) {
            next.delete('page');
          }

          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  // Update page (separate for pagination controls)
  const updatePage = useCallback(
    (page: number) => {
      setFilters((prev) => ({ ...prev, page }));
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (page <= 1) {
            next.delete('page');
          } else {
            next.set('page', page.toString());
          }
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  // Data hook uses local state, not URL
  // With keepPreviousData: isLoading only true on first load, isFetching true during filter changes
  const { data, isLoading, error, isFetching } = useTrades({
    strategy_id: filters.strategy_id,
    outcome: filters.outcome === 'all' ? undefined : filters.outcome,
    date_from: filters.date_from,
    date_to: filters.date_to,
    limit: ITEMS_PER_PAGE,
    offset: (filters.page - 1) * ITEMS_PER_PAGE,
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

      {/* Filters - controlled by local state */}
      <motion.div variants={staggerItem}>
        <TradeFilters filters={filters} onFiltersChange={updateFilters} />
      </motion.div>

      {/* Stats bar - container persists, content transitions */}
      <motion.div variants={staggerItem}>
        {isLoading ? (
          <TradeStatsBarSkeleton />
        ) : data ? (
          <TradeStatsBar
            trades={data.trades}
            totalCount={data.total_count}
            isTransitioning={isFetching}
          />
        ) : null}
      </motion.div>

      {/* Content area - container persists, content transitions */}
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
            isTransitioning={isFetching}
            currentPage={filters.page}
            onPageChange={updatePage}
            hasFilters={Boolean(
              filters.strategy_id ||
                filters.outcome !== 'all' ||
                filters.date_from ||
                filters.date_to
            )}
          />
        ) : null}
      </motion.div>
    </motion.div>
  );
}
