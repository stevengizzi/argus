/**
 * Shadow Trades tab for the Trade Log page.
 *
 * Displays counterfactual (rejected) signal positions from the
 * CounterfactualTracker with theoretical P&L, R-multiples, and MFE/MAE.
 *
 * Sprint 32.5, Session 6 — DEF-131.
 */

import { useState } from 'react';
import { Ghost, ChevronLeft, ChevronRight } from 'lucide-react';
import { useShadowTrades } from '../../hooks/useShadowTrades';
import { useStrategies } from '../../hooks/useStrategies';
import { GRADE_COLORS } from '../../constants/qualityConstants';
import type { ShadowTrade } from '../../api/types';

// --- Constants ---

const PAGE_SIZE = 50;

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
  if (!grade) return <span className="text-argus-text-muted text-xs">—</span>;
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
  if (value === null) return <span className="text-argus-text-muted text-xs">—</span>;
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
  if (value === null) return <span className="text-argus-text-muted text-xs">—</span>;
  const isPositive = value >= 0;
  return (
    <span className={isPositive ? 'text-argus-profit' : 'text-argus-loss'}>
      {isPositive ? '+' : ''}{value.toFixed(2)}R
    </span>
  );
}

// --- Summary stats ---

interface SummaryStatsProps {
  trades: ShadowTrade[];
  totalCount: number;
}

function SummaryStats({ trades, totalCount }: SummaryStatsProps) {
  const closed = trades.filter((t) => t.theoretical_pnl !== null);
  const wins = closed.filter((t) => (t.theoretical_pnl ?? 0) > 0);
  const winRate = closed.length > 0 ? wins.length / closed.length : null;
  const avgPnl =
    closed.length > 0
      ? closed.reduce((sum, t) => sum + (t.theoretical_pnl ?? 0), 0) / closed.length
      : null;
  const withR = trades.filter((t) => t.theoretical_r_multiple !== null);
  const avgR =
    withR.length > 0
      ? withR.reduce((sum, t) => sum + (t.theoretical_r_multiple ?? 0), 0) / withR.length
      : null;

  const statClass = 'flex flex-col gap-0.5';
  const labelClass = 'text-xs text-argus-text-muted uppercase tracking-wide';
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
}

function ShadowFilters({ filters, onFiltersChange }: ShadowFiltersProps) {
  const { data: strategiesData } = useStrategies();
  const strategies = strategiesData?.strategies ?? [];

  return (
    <div className="flex flex-wrap gap-3 items-end">
      {/* Strategy selector */}
      <div className="flex flex-col gap-1">
        <label className="text-xs text-argus-text-muted">Strategy</label>
        <select
          className="bg-argus-surface border border-argus-border rounded-md px-3 py-1.5 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
          value={filters.strategy_id ?? ''}
          onChange={(e) =>
            onFiltersChange({ strategy_id: e.target.value || undefined })
          }
        >
          <option value="">All strategies</option>
          {strategies.map((s) => (
            <option key={s.strategy_id} value={s.strategy_id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      {/* Rejection stage selector */}
      <div className="flex flex-col gap-1">
        <label className="text-xs text-argus-text-muted">Rejection Stage</label>
        <select
          className="bg-argus-surface border border-argus-border rounded-md px-3 py-1.5 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
          value={filters.rejection_stage ?? ''}
          onChange={(e) =>
            onFiltersChange({ rejection_stage: e.target.value || undefined })
          }
        >
          <option value="">All stages</option>
          {ALL_STAGES.map((stage) => (
            <option key={stage} value={stage}>
              {REJECTION_STAGE_LABELS[stage]}
            </option>
          ))}
        </select>
      </div>

      {/* Date range */}
      <div className="flex flex-col gap-1">
        <label className="text-xs text-argus-text-muted">From</label>
        <input
          type="date"
          className="bg-argus-surface border border-argus-border rounded-md px-3 py-1.5 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
          value={filters.date_from ?? ''}
          onChange={(e) =>
            onFiltersChange({ date_from: e.target.value || undefined })
          }
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-argus-text-muted">To</label>
        <input
          type="date"
          className="bg-argus-surface border border-argus-border rounded-md px-3 py-1.5 text-sm text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
          value={filters.date_to ?? ''}
          onChange={(e) =>
            onFiltersChange({ date_to: e.target.value || undefined })
          }
        />
      </div>
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
      <Ghost className="w-10 h-10 text-argus-text-muted opacity-40" />
      <p className="text-argus-text-muted text-sm max-w-sm">
        No shadow trades recorded yet. Shadow trades appear when signals are rejected by the
        quality filter, position sizer, or risk manager.
      </p>
    </div>
  );
}

// --- Table ---

interface ShadowTableProps {
  trades: ShadowTrade[];
}

function ShadowTable({ trades }: ShadowTableProps) {
  const thClass =
    'px-3 py-2 text-left text-xs font-medium text-argus-text-muted uppercase tracking-wide whitespace-nowrap';
  const tdClass =
    'px-3 py-2 text-sm text-argus-text whitespace-nowrap';

  return (
    <div
      className="overflow-x-auto rounded-lg border border-argus-border"
      data-testid="shadow-trade-table"
    >
      <table className="min-w-full divide-y divide-argus-border">
        <thead className="bg-argus-surface-2">
          <tr>
            <th className={thClass}>Symbol</th>
            <th className={thClass}>Strategy</th>
            <th className={thClass}>Variant</th>
            <th className={thClass}>Entry Time</th>
            <th className={thClass}>Entry $</th>
            <th className={thClass}>Exit $</th>
            <th className={thClass}>Theo P&L</th>
            <th className={thClass}>R-Multiple</th>
            <th className={thClass}>MFE (R)</th>
            <th className={thClass}>MAE (R)</th>
            <th className={thClass}>Stage</th>
            <th className={thClass}>Reason</th>
            <th className={thClass}>Grade</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-argus-border bg-argus-surface opacity-80">
          {trades.map((trade) => {
            const entryDate = new Date(trade.opened_at);
            const entryDisplay = `${entryDate.toLocaleDateString()} ${entryDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
            return (
              <tr
                key={trade.position_id}
                className="hover:bg-argus-surface-2/60 transition-colors"
                data-testid="shadow-trade-row"
              >
                <td className={`${tdClass} font-semibold`}>{trade.symbol}</td>
                <td className={tdClass}>{trade.strategy_id}</td>
                <td className={`${tdClass} text-argus-text-muted`}>
                  {trade.variant_id ?? '—'}
                </td>
                <td className={`${tdClass} text-argus-text-muted`}>{entryDisplay}</td>
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
                  <RMultipleCell value={trade.max_favorable_excursion} />
                </td>
                <td className={tdClass}>
                  <RMultipleCell value={trade.max_adverse_excursion} />
                </td>
                <td className={tdClass}>
                  <StageBadge stage={trade.rejection_stage} />
                </td>
                <td className={`${tdClass} text-argus-text-muted max-w-[180px] truncate`}>
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
    </div>
  );
}

// --- Pagination ---

interface PaginationProps {
  offset: number;
  limit: number;
  totalCount: number;
  onOffsetChange: (offset: number) => void;
}

function Pagination({ offset, limit, totalCount, onOffsetChange }: PaginationProps) {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(totalCount / limit));
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between text-sm text-argus-text-muted">
      <span>
        Page {currentPage} of {totalPages} ({totalCount} total)
      </span>
      <div className="flex gap-2">
        <button
          onClick={() => onOffsetChange(Math.max(0, offset - limit))}
          disabled={offset === 0}
          className="flex items-center gap-1 px-3 py-1.5 rounded border border-argus-border bg-argus-surface hover:bg-argus-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft className="w-3 h-3" />
          Prev
        </button>
        <button
          onClick={() => onOffsetChange(offset + limit)}
          disabled={offset + limit >= totalCount}
          className="flex items-center gap-1 px-3 py-1.5 rounded border border-argus-border bg-argus-surface hover:bg-argus-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Next
          <ChevronRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

// --- Main component ---

export function ShadowTradesTab() {
  const [filters, setFilters] = useState<FiltersState>({
    strategy_id: undefined,
    date_from: undefined,
    date_to: undefined,
    rejection_stage: undefined,
  });
  const [offset, setOffset] = useState(0);

  const updateFilters = (updates: Partial<FiltersState>) => {
    setFilters((prev) => ({ ...prev, ...updates }));
    setOffset(0); // reset pagination on filter change
  };

  const { data, isLoading, error } = useShadowTrades({
    ...filters,
    limit: PAGE_SIZE,
    offset,
  });

  const trades = data?.positions ?? [];
  const totalCount = data?.total_count ?? 0;

  return (
    <div className="space-y-4" data-testid="shadow-trades-tab">
      <ShadowFilters filters={filters} onFiltersChange={updateFilters} />

      {isLoading ? (
        <div className="py-16 text-center text-argus-text-muted text-sm">
          Loading shadow trades…
        </div>
      ) : error ? (
        <div className="py-8 text-center text-argus-loss text-sm">
          Error loading shadow trades: {error.message}
        </div>
      ) : trades.length === 0 ? (
        <>
          <SummaryStats trades={[]} totalCount={0} />
          <EmptyState />
        </>
      ) : (
        <>
          <SummaryStats trades={trades} totalCount={totalCount} />
          <ShadowTable trades={trades} />
          <Pagination
            offset={offset}
            limit={PAGE_SIZE}
            totalCount={totalCount}
            onOffsetChange={setOffset}
          />
        </>
      )}
    </div>
  );
}
