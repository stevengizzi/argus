/**
 * Trade table with pagination, row coloring, strategy badges, and exit reason badges.
 *
 * Three responsive breakpoints:
 * - Phone (<640px): Date/Symbol combined, Strategy, P&L, Exit Reason
 * - Tablet (640-1023px): Date, Symbol, Strategy, Entry, Exit, P&L ($), R, Exit Reason
 * - Desktop (≥1024px): Date, Symbol, Strategy, Side, Entry Price, Exit Price, P&L ($), P&L (R), Shares, Exit Reason, Hold Duration, Commission
 *
 * Updated with StrategyBadge (17-D).
 */

import { ChevronLeft, ChevronRight, Filter, BarChart3 } from 'lucide-react';
import { Badge, StrategyBadge } from '../../components/Badge';
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

interface TradeTableProps {
  trades: Trade[];
  totalCount: number;
  limit: number;
  isLoading?: boolean;
  isTransitioning?: boolean;
  /** Current page number (1-indexed) */
  currentPage: number;
  /** Callback when page changes */
  onPageChange: (page: number) => void;
  /** Whether any filters are currently active */
  hasFilters?: boolean;
  /** Callback when a trade row is clicked */
  onTradeClick?: (trade: Trade) => void;
}

const ITEMS_PER_PAGE = 20;

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
  limit,
  isLoading,
  isTransitioning = false,
  currentPage,
  onPageChange,
  hasFilters = false,
  onTradeClick,
}: TradeTableProps) {
  const openSymbolDetail = useSymbolDetailUI((state) => state.open);
  const totalPages = Math.ceil(totalCount / (limit || ITEMS_PER_PAGE));

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

  return (
    <div className="bg-argus-surface border border-argus-border rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full table-fixed">
          <thead className="sticky top-0 z-10">
            <tr className="bg-argus-surface-2">
              {/* Phone: combined date/symbol column */}
              <th className="lg:hidden px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-left">
                Trade
              </th>
              {/* Desktop: separate date column */}
              <th className="hidden lg:table-cell w-[100px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-left">
                Date
              </th>
              {/* Desktop: separate symbol column */}
              <th className="hidden lg:table-cell w-[80px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-left">
                Symbol
              </th>
              {/* Tablet+: strategy */}
              <th className="hidden md:table-cell w-[70px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-left">
                Strat
              </th>
              {/* Desktop only: side */}
              <th className="hidden lg:table-cell w-[55px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-left">
                Side
              </th>
              {/* Tablet+: entry price */}
              <th className="hidden md:table-cell w-[85px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right">
                Entry
              </th>
              {/* Tablet+: exit price */}
              <th className="hidden md:table-cell w-[85px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right">
                Exit
              </th>
              {/* All: P&L */}
              <th className="w-[90px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right">
                P&L
              </th>
              {/* Tablet+: R-multiple */}
              <th className="hidden md:table-cell w-[60px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right">
                R
              </th>
              {/* Desktop only: shares */}
              <th className="hidden lg:table-cell w-[65px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right">
                Shares
              </th>
              {/* All: exit reason */}
              <th className="w-[60px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-center">
                Exit
              </th>
              {/* Desktop only: hold duration */}
              <th className="hidden lg:table-cell w-[80px] px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim text-right">
                Duration
              </th>
            </tr>
          </thead>
          {/* Table body dims during filter transitions */}
          <tbody
            className={`divide-y divide-argus-border transition-opacity duration-200 ${
              isTransitioning ? 'opacity-40' : 'opacity-100'
            }`}
          >
            {trades.map((trade) => {
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

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-argus-border bg-argus-surface-2">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1}
            className="flex items-center justify-center gap-1 min-w-[44px] min-h-[44px] px-3 text-sm rounded-md border border-argus-border bg-argus-surface hover:bg-argus-surface-3 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Prev</span>
          </button>

          <span className="text-sm text-argus-text-dim tabular-nums">
            Page {currentPage} of {totalPages}
          </span>

          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages}
            className="flex items-center justify-center gap-1 min-w-[44px] min-h-[44px] px-3 text-sm rounded-md border border-argus-border bg-argus-surface hover:bg-argus-surface-3 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <span className="hidden sm:inline">Next</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
