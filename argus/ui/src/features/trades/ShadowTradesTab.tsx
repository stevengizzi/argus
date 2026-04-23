/**
 * Shadow Trades tab for the Trade Log page.
 *
 * Displays counterfactual (rejected) signal positions from the
 * CounterfactualTracker with theoretical P&L, R-multiples, and MFE/MAE.
 *
 * Sprint 32.5, Session 6 — DEF-131.
 * Sprint 32.8, Session 5 — outcome toggle, time presets, infinite scroll,
 *   sortable columns, wider Reason column with tooltip.
 */

import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { Ghost, Loader2, ChevronUp, ChevronDown } from 'lucide-react';
import { useShadowTrades } from '../../hooks/useShadowTrades';
import { useStrategies } from '../../hooks/useStrategies';
import { GRADE_COLORS } from '../../constants/qualityConstants';
import { SegmentedTab } from '../../components/SegmentedTab';
import { computeDateRangeForQuickFilter, type QuickFilter } from '../../stores/tradeFilters';
import type { ShadowTrade } from '../../api/types';
import type { SegmentedTabSegment } from '../../components/SegmentedTab';

// --- Constants ---

const PAGE_SIZE = 50;

type ShadowOutcomeFilter = 'all' | 'win' | 'loss' | 'be';

type SortKey =
  | 'symbol'
  | 'strategy_id'
  | 'opened_at'
  | 'entry_price'
  | 'theoretical_pnl'
  | 'theoretical_r_multiple'
  // Apr 21 debrief F-06 (IMPROMPTU-07, 2026-04-23): MFE/MAE columns
  // now sort on the R-multiple fields (`mfe_r`/`mae_r`) rather than
  // the dollar-valued `max_*_excursion` fields the UI previously fed
  // through RMultipleCell — that combination produced "$0.00R"
  // strings in the table. Backend still serializes the dollar fields
  // for backward compat; they're just no longer the column sort key.
  | 'mfe_r'
  | 'mae_r'
  | 'rejection_stage'
  | 'quality_grade';

type SortDir = 'asc' | 'desc';

const REJECTION_STAGE_COLORS: Record<string, string> = {
  QUALITY_FILTER: '#60a5fa',   // blue-400
  POSITION_SIZER: '#a78bfa',   // violet-400
  RISK_MANAGER:   '#f87171',   // red-400
  SHADOW:         '#94a3b8',   // slate-400
  BROKER_OVERFLOW:'#fb923c',   // orange-400
};

const REJECTION_STAGE_LABELS: Record<string, string> = {
  QUALITY_FILTER:  'Quality Filter',
  POSITION_SIZER:  'Position Sizer',
  RISK_MANAGER:    'Risk Manager',
  SHADOW:          'Shadow Mode',
  BROKER_OVERFLOW: 'Broker Overflow',
};

const ALL_STAGES = Object.keys(REJECTION_STAGE_LABELS);

// --- Sub-components ---

interface StageBadgeProps {
  stage: string;
}

function StageBadge({ stage }: StageBadgeProps) {
  const color = REJECTION_STAGE_COLORS[stage] ?? '#94a3b8';
  const label = REJECTION_STAGE_LABELS[stage] ?? stage;
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
      style={{ backgroundColor: `${color}22`, color }}
    >
      {label}
    </span>
  );
}

interface GradeBadgeProps {
  grade: string | null;
}

function GradeBadge({ grade }: GradeBadgeProps) {
  if (!grade) return <span className="text-argus-text-dim text-xs">—</span>;
  const color = GRADE_COLORS[grade] ?? '#9ca3af';
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold"
      style={{ backgroundColor: `${color}22`, color }}
    >
      {grade}
    </span>
  );
}

interface PnlCellProps {
  value: number | null;
}

function PnlCell({ value }: PnlCellProps) {
  if (value === null) return <span className="text-argus-text-dim text-xs">—</span>;
  const isPositive = value >= 0;
  const sign = isPositive ? '+' : '-';
  return (
    <span className={isPositive ? 'text-argus-profit' : 'text-argus-loss'}>
      {sign}${Math.abs(value).toFixed(2)}
    </span>
  );
}

interface RMultipleCellProps {
  value: number | null;
}

function RMultipleCell({ value }: RMultipleCellProps) {
  if (value === null) return <span className="text-argus-text-dim text-xs">—</span>;
  const isPositive = value >= 0;
  return (
    <span className={isPositive ? 'text-argus-profit' : 'text-argus-loss'}>
      {isPositive ? '+' : ''}{value.toFixed(2)}R
    </span>
  );
}

// --- Summary stats ---

interface SummaryStatsProps {
  winRate: number | null;
  avgPnl: number | null;
  avgR: number | null;
  totalCount: number;
}

function SummaryStats({ winRate, avgPnl, avgR, totalCount }: SummaryStatsProps) {

  const statClass = 'flex flex-col gap-0.5';
  const labelClass = 'text-xs text-argus-text-dim uppercase tracking-wide';
  const valueClass = 'text-sm font-semibold text-argus-text';

  return (
    <div
      className="grid grid-cols-2 sm:grid-cols-4 gap-4 px-4 py-3 rounded-lg border border-argus-border bg-argus-surface-2/50"
      data-testid="shadow-summary-stats"
    >
      <div className={statClass}>
        <span className={labelClass}>Shadow Trades</span>
        <span className={valueClass}>{totalCount}</span>
      </div>
      <div className={statClass}>
        <span className={labelClass}>Win Rate (theoretical)</span>
        <span className={valueClass}>
          {winRate !== null ? `${(winRate * 100).toFixed(1)}%` : '—'}
        </span>
      </div>
      <div className={statClass}>
        <span className={labelClass}>Avg Theo P&L</span>
        <span className={valueClass}>
          {avgPnl !== null ? (
            <span className={avgPnl >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
              {avgPnl >= 0 ? '+' : ''}${avgPnl.toFixed(2)}
            </span>
          ) : (
            '—'
          )}
        </span>
      </div>
      <div className={statClass}>
        <span className={labelClass}>Avg R-Multiple</span>
        <span className={valueClass}>
          {avgR !== null ? (
            <span className={avgR >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
              {avgR >= 0 ? '+' : ''}{avgR.toFixed(2)}R
            </span>
          ) : (
            '—'
          )}
        </span>
      </div>
    </div>
  );
}

// --- Filters ---

interface FiltersState {
  strategy_id: string | undefined;
  date_from: string | undefined;
  date_to: string | undefined;
  rejection_stage: string | undefined;
}

interface ShadowFiltersProps {
  filters: FiltersState;
  onFiltersChange: (updates: Partial<FiltersState>) => void;
  outcome: ShadowOutcomeFilter;
  onOutcomeChange: (outcome: ShadowOutcomeFilter) => void;
  quickFilter: QuickFilter;
  onQuickFilterChange: (label: QuickFilter) => void;
}

function ShadowFilters({
  filters,
  onFiltersChange,
  outcome,
  onOutcomeChange,
  quickFilter,
  onQuickFilterChange,
}: ShadowFiltersProps) {
  const { data: strategiesData } = useStrategies();
  const strategies = strategiesData?.strategies ?? [];

  const outcomeSegments: SegmentedTabSegment[] = [
    { label: 'All', value: 'all' },
    { label: 'Wins', value: 'win', countVariant: 'success' as const },
    { label: 'Losses', value: 'loss', countVariant: 'danger' as const },
    { label: 'BE', value: 'be' },
  ];

  return (
    <div className="bg-argus-surface-2/50 border border-argus-border rounded-lg px-4 py-2 flex flex-wrap items-center gap-2">
      {/* Strategy selector */}
      <select
        aria-label="Strategy"
        className="h-8 bg-argus-surface-2 border border-argus-border rounded-md px-3 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
        value={filters.strategy_id ?? ''}
        onChange={(e) => onFiltersChange({ strategy_id: e.target.value || undefined })}
      >
        <option value="">All strategies</option>
        {strategies.map((s) => (
          <option key={s.strategy_id} value={s.strategy_id}>
            {s.name}
          </option>
        ))}
      </select>

      {/* Rejection stage selector */}
      <select
        aria-label="Rejection Stage"
        className="h-8 bg-argus-surface-2 border border-argus-border rounded-md px-3 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
        value={filters.rejection_stage ?? ''}
        onChange={(e) => onFiltersChange({ rejection_stage: e.target.value || undefined })}
      >
        <option value="">All stages</option>
        {ALL_STAGES.map((stage) => (
          <option key={stage} value={stage}>
            {REJECTION_STAGE_LABELS[stage]}
          </option>
        ))}
      </select>

      {/* Outcome toggle */}
      <SegmentedTab
        segments={outcomeSegments}
        activeValue={outcome}
        onChange={(v) => onOutcomeChange(v as ShadowOutcomeFilter)}
        size="sm"
        layoutId="shadow-outcome-filter"
      />

      {/* Time preset buttons */}
      {(['today', 'week', 'month', 'all'] as const).map((label) => (
        <button
          key={label}
          onClick={() => onQuickFilterChange(label)}
          className={`h-8 px-3 text-xs rounded transition-colors ${
            quickFilter === label
              ? 'bg-argus-accent text-white'
              : 'bg-argus-surface-2 text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-3'
          }`}
          data-testid={`shadow-quick-filter-${label}`}
        >
          {label === 'today'
            ? 'Today'
            : label === 'week'
            ? 'Week'
            : label === 'month'
            ? 'Month'
            : 'All'}
        </button>
      ))}

      {/* Date range */}
      <input
        type="date"
        aria-label="From date"
        className="h-8 bg-argus-surface-2 border border-argus-border rounded-md px-3 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
        value={filters.date_from ?? ''}
        onChange={(e) => onFiltersChange({ date_from: e.target.value || undefined })}
        data-testid="shadow-date-from"
      />
      <input
        type="date"
        aria-label="To date"
        className="h-8 bg-argus-surface-2 border border-argus-border rounded-md px-3 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
        value={filters.date_to ?? ''}
        onChange={(e) => onFiltersChange({ date_to: e.target.value || undefined })}
        data-testid="shadow-date-to"
      />
    </div>
  );
}

// --- Empty state ---

function EmptyState() {
  return (
    <div
      className="flex flex-col items-center justify-center py-16 gap-4 text-center"
      data-testid="shadow-empty-state"
    >
      <Ghost className="w-10 h-10 text-argus-text-dim opacity-40" />
      <p className="text-argus-text-dim text-sm max-w-sm">
        No shadow trades recorded yet. Shadow trades appear when signals are rejected by the
        quality filter, position sizer, or risk manager.
      </p>
    </div>
  );
}

// --- Table ---

interface ShadowTableProps {
  trades: ShadowTrade[];
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
  sentinelRef: React.RefObject<HTMLDivElement>;
  isLoadingMore: boolean;
}

function ShadowTable({
  trades,
  sortKey,
  sortDir,
  onSort,
  sentinelRef,
  isLoadingMore,
}: ShadowTableProps) {
  const sortableClass =
    'cursor-pointer select-none hover:text-argus-text transition-colors';
  const thClass =
    'px-3 py-2 text-left text-xs font-medium text-argus-text-dim uppercase tracking-wide whitespace-nowrap';
  const tdClass = 'px-3 py-2 text-sm text-argus-text whitespace-nowrap';

  function SortIndicator({ col }: { col: SortKey }) {
    if (sortKey !== col) return null;
    return sortDir === 'asc' ? (
      <ChevronUp className="w-3 h-3 inline-block ml-0.5" />
    ) : (
      <ChevronDown className="w-3 h-3 inline-block ml-0.5" />
    );
  }

  return (
    <div
      className="overflow-x-auto rounded-lg border border-argus-border"
      data-testid="shadow-trade-table"
    >
      <table className="min-w-full divide-y divide-argus-border">
        <thead className="bg-argus-surface-2">
          <tr>
            <th
              className={`${thClass} ${sortableClass}`}
              onClick={() => onSort('symbol')}
              data-testid="sort-symbol"
            >
              Symbol
              <SortIndicator col="symbol" />
            </th>
            <th
              className={`${thClass} ${sortableClass}`}
              onClick={() => onSort('strategy_id')}
              data-testid="sort-strategy_id"
            >
              Strategy
              <SortIndicator col="strategy_id" />
            </th>
            <th className={thClass}>Variant</th>
            <th
              className={`${thClass} ${sortableClass}`}
              onClick={() => onSort('opened_at')}
              data-testid="sort-opened_at"
            >
              Entry Time
              <SortIndicator col="opened_at" />
            </th>
            <th
              className={`${thClass} ${sortableClass}`}
              onClick={() => onSort('entry_price')}
              data-testid="sort-entry_price"
            >
              Entry $
              <SortIndicator col="entry_price" />
            </th>
            <th className={thClass}>Exit $</th>
            <th
              className={`${thClass} ${sortableClass}`}
              onClick={() => onSort('theoretical_pnl')}
              data-testid="sort-theoretical_pnl"
            >
              Theo P&L
              <SortIndicator col="theoretical_pnl" />
            </th>
            <th
              className={`${thClass} ${sortableClass}`}
              onClick={() => onSort('theoretical_r_multiple')}
              data-testid="sort-theoretical_r_multiple"
            >
              R-Multiple
              <SortIndicator col="theoretical_r_multiple" />
            </th>
            <th
              className={`${thClass} ${sortableClass}`}
              onClick={() => onSort('mfe_r')}
              data-testid="sort-mfe_r"
            >
              MFE (R)
              <SortIndicator col="mfe_r" />
            </th>
            <th
              className={`${thClass} ${sortableClass}`}
              onClick={() => onSort('mae_r')}
              data-testid="sort-mae_r"
            >
              MAE (R)
              <SortIndicator col="mae_r" />
            </th>
            <th
              className={`${thClass} ${sortableClass}`}
              onClick={() => onSort('rejection_stage')}
              data-testid="sort-rejection_stage"
            >
              Stage
              <SortIndicator col="rejection_stage" />
            </th>
            <th className={`${thClass} min-w-[200px]`}>Reason</th>
            <th
              className={`${thClass} ${sortableClass}`}
              onClick={() => onSort('quality_grade')}
              data-testid="sort-quality_grade"
            >
              Grade
              <SortIndicator col="quality_grade" />
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-argus-border bg-argus-surface opacity-80">
          {trades.map((trade) => {
            const entryDate = new Date(trade.opened_at);
            const entryDisplay = `${entryDate.toLocaleDateString()} ${entryDate.toLocaleTimeString(
              [],
              { hour: '2-digit', minute: '2-digit' }
            )}`;
            return (
              <tr
                key={trade.position_id}
                className="hover:bg-argus-surface-2/60 transition-colors"
                data-testid="shadow-trade-row"
              >
                <td className={`${tdClass} font-semibold`}>{trade.symbol}</td>
                <td className={tdClass}>{trade.strategy_id}</td>
                <td className={`${tdClass} text-argus-text-dim`}>
                  {trade.variant_id ?? '—'}
                </td>
                <td className={`${tdClass} text-argus-text-dim`}>{entryDisplay}</td>
                <td className={tdClass}>${trade.entry_price.toFixed(2)}</td>
                <td className={tdClass}>
                  {trade.exit_price !== null ? `$${trade.exit_price.toFixed(2)}` : '—'}
                </td>
                <td className={tdClass}>
                  <PnlCell value={trade.theoretical_pnl} />
                </td>
                <td className={tdClass}>
                  <RMultipleCell value={trade.theoretical_r_multiple} />
                </td>
                <td className={tdClass}>
                  <RMultipleCell value={trade.mfe_r} />
                </td>
                <td className={tdClass}>
                  <RMultipleCell value={trade.mae_r} />
                </td>
                <td className={tdClass}>
                  <StageBadge stage={trade.rejection_stage} />
                </td>
                <td
                  className={`${tdClass} text-argus-text-dim min-w-[200px] max-w-[280px] truncate`}
                  title={trade.rejection_reason}
                  data-testid="reason-cell"
                >
                  {trade.rejection_reason}
                </td>
                <td className={tdClass}>
                  <GradeBadge grade={trade.quality_grade} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Sentinel element for IntersectionObserver */}
      <div ref={sentinelRef} data-testid="shadow-scroll-sentinel" />

      {/* Bottom loading indicator */}
      {isLoadingMore && (
        <div
          className="flex justify-center py-3"
          data-testid="shadow-loading-more"
        >
          <Loader2 className="w-4 h-4 animate-spin text-argus-text-dim" />
        </div>
      )}
    </div>
  );
}

// --- Main component ---

interface ShadowTradesTabProps {
  enabled?: boolean;
}

export function ShadowTradesTab({ enabled = true }: ShadowTradesTabProps) {
  const [filters, setFilters] = useState<FiltersState>({
    strategy_id: undefined,
    date_from: undefined,
    date_to: undefined,
    rejection_stage: undefined,
  });
  const [outcome, setOutcome] = useState<ShadowOutcomeFilter>('all');
  const [quickFilter, setQuickFilter] = useState<QuickFilter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('opened_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [offset, setOffset] = useState(0);
  const [allTrades, setAllTrades] = useState<ShadowTrade[]>([]);

  const sentinelRef = useRef<HTMLDivElement>(null);

  // CounterfactualStore uses raw string comparison on opened_at (ISO datetime).
  // Append end-of-day time to date_to so records with a time component are included.
  const apiDateTo = filters.date_to ? `${filters.date_to}T23:59:59` : filters.date_to;

  // Accumulate pages; deduplicate by position_id to handle keepPreviousData stale returns
  const { data, isLoading, isFetching, error, isPlaceholderData } = useShadowTrades(
    { ...filters, date_to: apiDateTo, limit: PAGE_SIZE, offset },
    enabled,
  );

  // Guard against keepPreviousData returning stale results from prior filter params.
  // Without this check, the effect would repopulate allTrades with old positions while
  // totalCount already reflects the new filter — causing stats to appear "stuck".
  useEffect(() => {
    if (!data || isPlaceholderData) return;
    setAllTrades((prev) => {
      if (offset === 0) return data.positions;
      const existingIds = new Set(prev.map((t) => t.position_id));
      const newTrades = data.positions.filter((t) => !existingIds.has(t.position_id));
      return newTrades.length > 0 ? [...prev, ...newTrades] : prev;
    });
  }, [data, offset, isPlaceholderData]);

  const hasMore = data ? offset + PAGE_SIZE < data.total_count : false;
  const totalCount = data?.total_count ?? 0;

  const loadMore = useCallback(() => {
    if (!hasMore || isFetching) return;
    setOffset((prev) => prev + PAGE_SIZE);
  }, [hasMore, isFetching]);

  // IntersectionObserver wired to sentinel at bottom of table
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadMore();
      },
      { threshold: 0.1 }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [loadMore]);

  const updateFilters = useCallback((updates: Partial<FiltersState>) => {
    setFilters((prev) => ({ ...prev, ...updates }));
    setOffset(0);
    setAllTrades([]);
  }, []);

  const handleQuickFilterChange = useCallback(
    (label: QuickFilter) => {
      if (label === quickFilter) return;
      setQuickFilter(label);
      const { dateFrom, dateTo } = computeDateRangeForQuickFilter(label);
      updateFilters({ date_from: dateFrom, date_to: dateTo });
    },
    [updateFilters, quickFilter]
  );

  const handleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDir((dir) => (dir === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortKey(key);
        setSortDir('desc');
      }
    },
    [sortKey]
  );

  // Client-side outcome filter then sort
  const displayTrades = useMemo(() => {
    const filtered =
      outcome === 'all'
        ? allTrades
        : allTrades.filter((t) => {
            if (outcome === 'win') return t.theoretical_pnl !== null && t.theoretical_pnl > 0;
            if (outcome === 'loss') return t.theoretical_pnl !== null && t.theoretical_pnl < 0;
            if (outcome === 'be') return t.theoretical_pnl === null || t.theoretical_pnl === 0;
            return true;
          });

    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey] as string | number | null;
      const bVal = b[sortKey] as string | number | null;
      if (aVal === null && bVal === null) return 0;
      if (aVal === null) return sortDir === 'asc' ? 1 : -1;
      if (bVal === null) return sortDir === 'asc' ? -1 : 1;
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [allTrades, outcome, sortKey, sortDir]);

  const isLoadingMore = isFetching && offset > 0;

  // Compute summary stats from the current allTrades snapshot.
  // useMemo ensures these recompute exactly when allTrades changes (e.g. on filter switch).
  const summaryStats = useMemo(() => {
    const withPnl = allTrades.filter((t) => t.theoretical_pnl !== null);
    const winRate =
      withPnl.length > 0
        ? withPnl.filter((t) => t.theoretical_pnl! > 0).length / withPnl.length
        : null;
    const avgPnl =
      withPnl.length > 0
        ? withPnl.reduce((sum, t) => sum + t.theoretical_pnl!, 0) / withPnl.length
        : null;
    const withR = allTrades.filter((t) => t.theoretical_r_multiple !== null);
    const avgR =
      withR.length > 0
        ? withR.reduce((sum, t) => sum + t.theoretical_r_multiple!, 0) / withR.length
        : null;
    return { winRate, avgPnl, avgR };
  }, [allTrades]);

  return (
    <div className="space-y-4" data-testid="shadow-trades-tab">
      <ShadowFilters
        filters={filters}
        onFiltersChange={updateFilters}
        outcome={outcome}
        onOutcomeChange={(o) => setOutcome(o)}
        quickFilter={quickFilter}
        onQuickFilterChange={handleQuickFilterChange}
      />

      {error ? (
        <div
          className="py-8 text-center text-argus-loss text-sm"
          data-testid="shadow-error-state"
        >
          Unable to load shadow trades: {error.message}
        </div>
      ) : isLoading || !data ? (
        <div
          className="flex items-center justify-center py-16 gap-2 text-argus-text-dim text-sm"
          data-testid="shadow-loading-state"
        >
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading shadow trades…
        </div>
      ) : allTrades.length === 0 ? (
        <>
          <SummaryStats winRate={null} avgPnl={null} avgR={null} totalCount={0} />
          <EmptyState />
        </>
      ) : (
        <>
          <SummaryStats
            winRate={summaryStats.winRate}
            avgPnl={summaryStats.avgPnl}
            avgR={summaryStats.avgR}
            totalCount={totalCount}
          />
          <ShadowTable
            trades={displayTrades}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={handleSort}
            sentinelRef={sentinelRef}
            isLoadingMore={isLoadingMore}
          />
        </>
      )}
    </div>
  );
}
