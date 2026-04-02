/**
 * Trade log page with filtering and scrollable table.
 *
 * Full trade history with strategy/outcome/date filters, summary stats, and scrollable table.
 *
 * Uses Zustand store for time filter persistence across navigation.
 * Containers and headers persist during filter changes - only data values transition.
 */

import { useState, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ScrollText, Download, AlertCircle, Ghost } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import {
  TradeFilters,
  TradeStatsBar,
  TradeTable,
  TradeDetailPanel,
  TradeStatsBarSkeleton,
  TradeTableSkeleton,
} from '../features/trades';
import { ShadowTradesTab } from '../features/trades/ShadowTradesTab';
import { useTrades } from '../hooks/useTrades';
import { useTradeStats } from '../hooks/useTradeStats';
import { staggerContainer, staggerItem } from '../utils/motion';
import { getToken } from '../api/client';
import type { Trade } from '../api/types';
import type { OutcomeFilter, TradeFilterValues } from '../hooks/useTradeFilters';
import { useCopilotContext } from '../hooks/useCopilotContext';
import { useTradeFiltersStore, computeDateRangeForQuickFilter } from '../stores/tradeFilters';

interface FilterState {
  strategy_id: string | undefined;
  outcome: OutcomeFilter;
  date_from: string | undefined;
  date_to: string | undefined;
}

type ActiveTab = 'live' | 'shadow';

export function TradesPage() {
  const [, setSearchParams] = useSearchParams();
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('live');

  // Keyboard shortcuts: 'l' → live tab, 's' → shadow tab
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (document.activeElement as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
      if (e.key === 'l') setActiveTab('live');
      if (e.key === 's') setActiveTab('shadow');
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Register Copilot context (defined early, uses state below)
  useCopilotContext('Trades', () => ({
    filters: {
      strategy: filters.strategy_id ?? 'all',
      outcome: filters.outcome,
      dateFrom: filters.date_from,
      dateTo: filters.date_to,
    },
    tradeCount: data?.total_count ?? 0,
    selectedTrade: selectedTrade ? {
      symbol: selectedTrade.symbol,
      pnl: selectedTrade.pnl_dollars,
      outcome: selectedTrade.pnl_dollars !== null
        ? (selectedTrade.pnl_dollars > 0 ? 'win' : selectedTrade.pnl_dollars < 0 ? 'loss' : 'breakeven')
        : null,
      strategy: selectedTrade.strategy_id,
    } : null,
  }));

  // Initialize from Zustand store (persists across navigation) + URL params for strategy/outcome
  const storeState = useTradeFiltersStore();
  const [filters, setFilters] = useState<FilterState>(() => {
    const params = new URLSearchParams(window.location.search);
    const outcomeParam = params.get('outcome');

    // Date range: prefer Zustand store (persists quick filter selection across navigation)
    const storeDates = computeDateRangeForQuickFilter(storeState.quickFilter);

    return {
      strategy_id: params.get('strategy') || undefined,
      outcome:
        outcomeParam === 'win' || outcomeParam === 'loss' || outcomeParam === 'breakeven'
          ? outcomeParam
          : 'all',
      date_from: storeDates.dateFrom,
      date_to: storeDates.dateTo,
    };
  });

  // Update both local state and URL
  const updateFilters = useCallback(
    (updates: Partial<TradeFilterValues>) => {
      setFilters((prev) => ({ ...prev, ...updates }));

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

          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  // Data hook uses local state — fetches all trades matching active filter (no pagination).
  // limit: 250 (backend max) ensures stats bar computes from the full filtered set,
  // not just the default 50-trade page. Without this, Win Rate / Net P&L are computed
  // from a truncated subset and appear unchanged when toggling date filters.
  const { data, isLoading, error, isFetching } = useTrades({
    strategy_id: filters.strategy_id,
    outcome: filters.outcome === 'all' ? undefined : filters.outcome,
    date_from: filters.date_from,
    date_to: filters.date_to,
    limit: 1000,
  });

  // Server-side stats (resolves DEF-102 / DEF-117)
  const { data: statsData, isFetching: statsFetching } = useTradeStats({
    strategy_id: filters.strategy_id,
    outcome: filters.outcome === 'all' ? undefined : filters.outcome,
    date_from: filters.date_from,
    date_to: filters.date_to,
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

      {/* Tab bar */}
      <motion.div variants={staggerItem}>
        <div className="flex gap-1 border-b border-argus-border" data-testid="trades-tab-bar">
          <button
            onClick={() => setActiveTab('live')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'live'
                ? 'border-argus-accent text-argus-accent'
                : 'border-transparent text-argus-text-dim hover:text-argus-text'
            }`}
            data-testid="tab-live-trades"
          >
            <ScrollText className="w-4 h-4" />
            Live Trades
          </button>
          <button
            onClick={() => setActiveTab('shadow')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'shadow'
                ? 'border-argus-accent text-argus-accent'
                : 'border-transparent text-argus-text-dim hover:text-argus-text'
            }`}
            data-testid="tab-shadow-trades"
          >
            <Ghost className="w-4 h-4" />
            Shadow Trades
          </button>
        </div>
      </motion.div>

      {/* Live Trades tab content — always mounted to avoid remount reinitialization issues */}
      <div className={activeTab === 'live' ? undefined : 'hidden'}>
        {/* Filters - controlled by local state */}
        <motion.div variants={staggerItem}>
          <TradeFilters filters={filters} onFiltersChange={updateFilters} />
        </motion.div>

        {/* Stats bar - container persists, content transitions */}
        <motion.div variants={staggerItem}>
          {isLoading ? (
            <TradeStatsBarSkeleton />
          ) : statsData ? (
            <TradeStatsBar
              stats={statsData}
              isTransitioning={isFetching || statsFetching}
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
              isLoading={isLoading}
              isTransitioning={isFetching}
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
      </div>

      {/* Shadow Trades tab content — always mounted, fetch disabled when hidden */}
      <div className={activeTab === 'shadow' ? undefined : 'hidden'}>
        <ShadowTradesTab enabled={activeTab === 'shadow'} />
      </div>
    </motion.div>
  );
}
