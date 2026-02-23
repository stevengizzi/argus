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
import { ScrollText, Download, AlertCircle } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import {
  TradeFilters,
  TradeStatsBar,
  TradeTable,
  TradeDetailPanel,
  TradeStatsBarSkeleton,
  TradeTableSkeleton,
} from '../features/trades';
import { useTrades } from '../hooks/useTrades';
import { staggerContainer, staggerItem } from '../utils/motion';
import { getToken } from '../api/client';
import type { Trade } from '../api/types';
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
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

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

  // Export trades as CSV
  const handleExportCsv = useCallback(async () => {
    setIsExporting(true);
    setExportError(null);
    try {
      const token = getToken();
      if (!token) {
        throw new Error('Not authenticated — please log in again');
      }

      const params = new URLSearchParams();
      if (filters.strategy_id) params.set('strategy_id', filters.strategy_id);
      if (filters.date_from) params.set('date_from', filters.date_from);
      if (filters.date_to) params.set('date_to', filters.date_to);

      const response = await fetch(
        `/api/v1/trades/export/csv${params.toString() ? `?${params}` : ''}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Export failed (${response.status})`);
      }

      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get('Content-Disposition');
      const filenameMatch = contentDisposition?.match(/filename="?([^"]+)"?/);
      const filename = filenameMatch?.[1] || 'argus_trades.csv';

      // Create blob and download
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Export failed';
      setExportError(message);
      console.error('Export failed:', err);
    } finally {
      setIsExporting(false);
    }
  }, [filters.strategy_id, filters.date_from, filters.date_to]);

  return (
    <motion.div
      className="space-y-4 md:space-y-6"
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      {/* Page header */}
      <motion.div className="flex flex-col gap-2" variants={staggerItem}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ScrollText className="w-6 h-6 text-argus-accent" />
            <h1 className="text-xl font-semibold text-argus-text">Trades</h1>
          </div>
          <button
            onClick={handleExportCsv}
            disabled={isExporting || isLoading}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-md border border-argus-border bg-argus-surface hover:bg-argus-surface-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">{isExporting ? 'Exporting...' : 'Export CSV'}</span>
          </button>
        </div>
        {exportError && (
          <div className="flex items-center gap-2 text-sm text-argus-loss bg-argus-loss/10 border border-argus-loss/20 rounded-md px-3 py-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{exportError}</span>
            <button
              onClick={() => setExportError(null)}
              className="ml-auto text-argus-loss hover:text-argus-loss/70"
            >
              ×
            </button>
          </div>
        )}
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
            onTradeClick={setSelectedTrade}
          />
        ) : null}
      </motion.div>

      {/* Trade detail panel */}
      <TradeDetailPanel
        trade={selectedTrade}
        onClose={() => setSelectedTrade(null)}
      />
    </motion.div>
  );
}
