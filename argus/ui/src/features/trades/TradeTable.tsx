/**
 * Trade table with scrollable body, sortable columns, row coloring, strategy badges, and exit reason badges.
 *
 * Three responsive breakpoints:
 * - Phone (<640px): Date/Symbol combined, Strategy, P&L, Exit Reason
 * - Tablet (640-1023px): Date, Symbol, Strategy, Entry, Exit, P&L ($), R, Exit Reason
 * - Desktop (≥1024px): Date, Symbol, Strategy, Side, Entry Price, Exit Price, P&L ($), P&L (R), Shares, Exit Reason, Hold Duration, Commission
 *
 * Updated with StrategyBadge (17-D).
 * Updated: pagination replaced with scrollable table + sortable columns (Sprint 25.6 S3).
 */

import { useState, useMemo, useCallback } from 'react';
import { ChevronUp, ChevronDown, Filter, BarChart3 } from 'lucide-react';
import { Badge, StrategyBadge } from '../../components/Badge';
import { QualityBadge } from '../../components/QualityBadge';
import { EmptyState } from '../../components/EmptyState';
import { useSymbolDetailUI } from '../../stores/symbolDetailUI';
import type { Trade } from '../../api/types';
import {
  formatDate,
  formatDuration,
  formatPnl,
  formatPrice,
  formatR,
} from '../../utils/format';
import { GRADE_ORDER } from '../../constants/qualityConstants';

export type SortDirection = 'asc' | 'desc';

export interface SortState {
  column: string;
  direction: SortDirection;
}

interface TradeTableProps {
  trades: Trade[];
  totalCount: number;
  isLoading?: boolean;
  isTransitioning?: boolean;
  /** Whether any filters are currently active */
  hasFilters?: boolean;
  /** Callback when a trade row is clicked */
  onTradeClick?: (trade: Trade) => void;
}

/**
 * Compare two trade values for sorting. Handles nulls by sorting them last.
 */
function compareTradeValues(a: number | string | null, b: number | string | null, direction: SortDirection): number {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  const cmp = a < b ? -1 : a > b ? 1 : 0;
  return direction === 'asc' ? cmp : -cmp;
}

/**
 * Get the sortable value from a trade for a given column key.
 */
function getTradeValue(trade: Trade, column: string): number | string | null {
  switch (column) {
    case 'symbol': return trade.symbol;
    case 'strategy': return trade.strategy_id;
    case 'entry_time': return trade.entry_time;
    case 'side': return trade.side;
    case 'pnl': return trade.pnl_dollars;
    case 'r_multiple': return trade.pnl_r_multiple;
    case 'quality': {
      const grade = trade.quality_grade;
      if (!grade) return null;
      const idx = GRADE_ORDER.indexOf(grade as typeof GRADE_ORDER[number]);
      return idx === -1 ? null : idx;
    }
    case 'exit_reason': return trade.exit_reason;
    case 'hold_duration': return trade.hold_duration_seconds;
    default: return null;
  }
}

/**
 * Get exit reason badge variant based on exit reason type.
 */
function getExitReasonVariant(
  exitReason: string | null
): 'success' | 'danger' | 'warning' | 'neutral' {
  if (!exitReason) return 'neutral';

  const reason = exitReason.toLowerCase();
  if (reason === 'target_1' || reason === 't1' || reason === 'target_2' || reason === 't2') {
    return 'success';
  }
  if (reason === 'stop_loss' || reason === 'sl' || reason === 'stop') {
    return 'danger';
  }
  if (reason === 'time_stop' || reason === 'time' || reason === 'timeout') {
    return 'warning';
  }
  if (reason === 'trailing_stop') {
    return 'warning';
  }
  if (reason === 'eod' || reason === 'end_of_day') {
    return 'neutral';
  }
  return 'neutral';
}

/**
 * Format exit reason for display.
 */
function formatExitReason(exitReason: string | null): string {
  if (!exitReason) return '—';

  const reason = exitReason.toLowerCase();
  if (reason === 'target_1') return 'T1';
  if (reason === 'target_2') return 'T2';
  if (reason === 'stop_loss') return 'SL';
  if (reason === 'time_stop' || reason === 'timeout') return 'TIME';
  if (reason === 'trailing_stop') return 'Trail';
  if (reason === 'end_of_day') return 'EOD';
  return exitReason.toUpperCase().replace('_', ' ');
}

/**
 * Get row background class based on trade outcome.
 */
function getRowBgClass(pnl: number | null): string {
  if (pnl === null) return '';
  if (pnl > 0) return 'bg-argus-profit/5 hover:bg-argus-profit/10';
  if (pnl < 0) return 'bg-argus-loss/5 hover:bg-argus-loss/10';
  return '';
}

export function TradeTable({
  trades,
  totalCount,
  isLoading,
  isTransitioning = false,
  hasFilters = false,
  onTradeClick,
}: TradeTableProps) {
  const openSymbolDetail = useSymbolDetailUI((state) => state.open);
  const [sort, setSort] = useState<SortState | null>(null);

  // Cycle sort: none → asc → desc → none
  const handleSort = useCallback((column: string) => {
    setSort((prev) => {
      if (!prev || prev.column !== column) return { column, direction: 'asc' };
      if (prev.direction === 'asc') return { column, direction: 'desc' };
      return null;
    });
  }, []);

  // Client-side sort
  const sortedTrades = useMemo(() => {
    if (!sort) return trades;
    return [...trades].sort((a, b) =>
      compareTradeValues(getTradeValue(a, sort.column), getTradeValue(b, sort.column), sort.direction)
    );
  }, [trades, sort]);

  // Handle symbol click - opens SymbolDetailPanel without triggering row click
  const handleSymbolClick = (e: React.MouseEvent, symbol: string) => {
    e.stopPropagation();
    openSymbolDetail(symbol);
  };

  if (trades.length === 0 && !isLoading) {
    const icon = hasFilters ? Filter : BarChart3;
    const message = hasFilters
      ? 'No trades match your filters — try adjusting the date range or strategy'
      : 'No trades recorded yet — trades appear here once the strategy takes a position';
    return <EmptyState icon={icon} message={message} />;
  }

  /** Render sort indicator for a column header. */
  const sortIndicator = (column: string) => {
    if (!sort || sort.column !== column) return null;
    return sort.direction === 'asc'
      ? <ChevronUp className="w-3 h-3 inline-block ml-0.5" />
      : <ChevronDown className="w-3 h-3 inline-block ml-0.5" />;
  };

  const sortableClass = 'cursor-pointer select-none hover:text-argus-text transition-colors';

  return (
    <div className="bg-argus-surface border border-argus-border rounded-lg overflow-hidden">
      {/* Scrollable container: ~20 rows visible */}
      <div className="overflow-x-auto overflow-y-auto max-h-[800px]" data-testid="trade-table-scroll">
        <table className="w-full table-fixed">
          <thead className="sticky top-0 z-10">
            <tr className="bg-argus-surface-2">
              {/* Phone: combined date/symbol column */}
              <th className="lg:hidden px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-left">
                Trade
              </th>
              {/* Desktop: separate date column — sortable by entry_time */}
              <th
                className={`hidden lg:table-cell w-[100px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-left ${sortableClass}`}
                onClick={() => handleSort('entry_time')}
                data-testid="sort-entry_time"
              >
                Date{sortIndicator('entry_time')}
              </th>
              {/* Desktop: separate symbol column — sortable */}
              <th
                className={`hidden lg:table-cell w-[80px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-left ${sortableClass}`}
                onClick={() => handleSort('symbol')}
                data-testid="sort-symbol"
              >
                Symbol{sortIndicator('symbol')}
              </th>
              {/* Tablet+: strategy — sortable */}
              <th
                className={`hidden md:table-cell w-[70px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-left ${sortableClass}`}
                onClick={() => handleSort('strategy')}
                data-testid="sort-strategy"
              >
                Strat{sortIndicator('strategy')}
              </th>
              {/* Desktop only: side — sortable */}
              <th
                className={`hidden lg:table-cell w-[55px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-left ${sortableClass}`}
                onClick={() => handleSort('side')}
                data-testid="sort-side"
              >
                Side{sortIndicator('side')}
              </th>
              {/* Tablet+: entry price */}
              <th className="hidden md:table-cell w-[85px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right">
                Entry
              </th>
              {/* Tablet+: exit price */}
              <th className="hidden md:table-cell w-[85px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right">
                Exit
              </th>
              {/* All: P&L — sortable */}
              <th
                className={`w-[90px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right ${sortableClass}`}
                onClick={() => handleSort('pnl')}
                data-testid="sort-pnl"
              >
                P&L{sortIndicator('pnl')}
              </th>
              {/* Tablet+: R-multiple — sortable */}
              <th
                className={`hidden md:table-cell w-[60px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right ${sortableClass}`}
                onClick={() => handleSort('r_multiple')}
                data-testid="sort-r_multiple"
              >
                R{sortIndicator('r_multiple')}
              </th>
              {/* Desktop only: shares */}
              <th className="hidden lg:table-cell w-[65px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right">
                Shares
              </th>
              {/* Tablet+: quality grade — sortable */}
              <th
                className={`hidden md:table-cell w-[60px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-center ${sortableClass}`}
                onClick={() => handleSort('quality')}
                data-testid="sort-quality"
              >
                Quality{sortIndicator('quality')}
              </th>
              {/* All: exit reason — sortable */}
              <th
                className={`w-[60px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-center ${sortableClass}`}
                onClick={() => handleSort('exit_reason')}
                data-testid="sort-exit_reason"
              >
                Exit{sortIndicator('exit_reason')}
              </th>
              {/* Desktop only: hold duration — sortable */}
              <th
                className={`hidden lg:table-cell w-[80px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right ${sortableClass}`}
                onClick={() => handleSort('hold_duration')}
                data-testid="sort-hold_duration"
              >
                Duration{sortIndicator('hold_duration')}
              </th>
            </tr>
          </thead>
          {/* Table body dims during filter transitions */}
          <tbody
            className={`divide-y divide-argus-border transition-opacity duration-200 ${
              isTransitioning ? 'opacity-40' : 'opacity-100'
            }`}
          >
            {sortedTrades.map((trade) => {
              const pnlFormatted = formatPnl(trade.pnl_dollars ?? 0);
              const rFormatted = formatR(trade.pnl_r_multiple ?? 0);

              return (
                <tr
                  key={trade.id}
                  onClick={() => onTradeClick?.(trade)}
                  className={`transition-colors duration-150 cursor-pointer ${getRowBgClass(trade.pnl_dollars)}`}
                >
                  {/* Phone: combined date/symbol with strategy badge */}
                  <td className="px-3 py-2.5 text-sm lg:hidden">
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => handleSymbolClick(e, trade.symbol)}
                          className="font-medium hover:text-argus-accent hover:underline transition-colors cursor-pointer"
                        >
                          {trade.symbol}
                        </button>
                        <StrategyBadge strategyId={trade.strategy_id} />
                      </div>
                      <span className="text-xs text-argus-text-dim">
                        {formatDate(trade.entry_time)}
                      </span>
                    </div>
                  </td>
                  {/* Desktop: date */}
                  <td className="hidden lg:table-cell px-3 py-2.5 text-sm tabular-nums text-argus-text-dim">
                    {formatDate(trade.entry_time)}
                  </td>
                  {/* Desktop: symbol */}
                  <td className="hidden lg:table-cell px-3 py-2.5 text-sm font-medium">
                    <button
                      onClick={(e) => handleSymbolClick(e, trade.symbol)}
                      className="hover:text-argus-accent hover:underline transition-colors cursor-pointer"
                    >
                      {trade.symbol}
                    </button>
                  </td>
                  {/* Tablet+: strategy badge */}
                  <td className="hidden md:table-cell px-3 py-2.5 text-sm">
                    <StrategyBadge strategyId={trade.strategy_id} />
                  </td>
                  {/* Desktop: side */}
                  <td className="hidden lg:table-cell px-3 py-2.5 text-sm">
                    <span
                      className={
                        trade.side === 'long' ? 'text-argus-profit' : 'text-argus-loss'
                      }
                    >
                      {trade.side.toUpperCase()}
                    </span>
                  </td>
                  {/* Tablet+: entry price */}
                  <td className="hidden md:table-cell px-3 py-2.5 text-sm tabular-nums text-right">
                    {formatPrice(trade.entry_price)}
                  </td>
                  {/* Tablet+: exit price */}
                  <td className="hidden md:table-cell px-3 py-2.5 text-sm tabular-nums text-right">
                    {trade.exit_price !== null ? formatPrice(trade.exit_price) : '—'}
                  </td>
                  {/* All: P&L */}
                  <td
                    className={`px-3 py-2.5 text-sm tabular-nums text-right font-medium ${pnlFormatted.className}`}
                  >
                    {trade.pnl_dollars !== null ? pnlFormatted.text : '—'}
                  </td>
                  {/* Tablet+: R-multiple */}
                  <td
                    className={`hidden md:table-cell px-3 py-2.5 text-sm tabular-nums text-right ${rFormatted.className}`}
                  >
                    {trade.pnl_r_multiple !== null ? rFormatted.text : '—'}
                  </td>
                  {/* Desktop: shares */}
                  <td className="hidden lg:table-cell px-3 py-2.5 text-sm tabular-nums text-right">
                    {trade.shares}
                  </td>
                  {/* Tablet+: quality grade */}
                  <td className="hidden md:table-cell px-3 py-2.5 text-center">
                    {trade.quality_grade ? (
                      <QualityBadge
                        grade={trade.quality_grade}
                        score={trade.quality_score ?? undefined}
                      />
                    ) : (
                      <span className="text-sm text-argus-text-dim">—</span>
                    )}
                  </td>
                  {/* All: exit reason */}
                  <td className="px-3 py-2.5 text-center">
                    <Badge variant={getExitReasonVariant(trade.exit_reason)}>
                      {formatExitReason(trade.exit_reason)}
                    </Badge>
                  </td>
                  {/* Desktop: hold duration */}
                  <td className="hidden lg:table-cell px-3 py-2.5 text-sm tabular-nums text-right text-argus-text-dim">
                    {trade.hold_duration_seconds !== null
                      ? formatDuration(trade.hold_duration_seconds)
                      : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Trade count footer */}
      <div className="px-4 py-2 border-t border-argus-border bg-argus-surface-2">
        <span className="text-xs text-argus-text-dim tabular-nums">
          {totalCount} {totalCount === 1 ? 'trade' : 'trades'}
        </span>
      </div>
    </div>
  );
}
