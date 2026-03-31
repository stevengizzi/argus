/**
 * Positions section with Open/Closed toggle and Table/Timeline view switch.
 *
 * Shows open positions with real-time price updates via WebSocket,
 * or today's closed trades, depending on selected tab.
 *
 * Updated with SegmentedTab for position view filter (17-B).
 * Added Timeline view for visualizing position durations (18-B).
 */

import { useState, useMemo } from 'react';
import { Clock, Moon, Radio, BarChart3, List, GanttChart } from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { EmptyState } from '../../components/EmptyState';
import { PnlValue } from '../../components/PnlValue';
import { Badge, StrategyBadge } from '../../components/Badge';
import { QualityBadge } from '../../components/QualityBadge';
import { SegmentedTab } from '../../components/SegmentedTab';
import { PositionTimeline } from '../../components/PositionTimeline';
import { TradeDetailPanel } from '../trades/TradeDetailPanel';
import { PositionDetailPanel } from './PositionDetailPanel';
import { usePositions } from '../../hooks/usePositions';
import { useTrades } from '../../hooks/useTrades';
import { useLiveStore } from '../../stores/live';
import { usePositionsUIStore } from '../../stores/positionsUI';
import { useSymbolDetailUI } from '../../stores/symbolDetailUI';
import { formatPrice, formatDuration, formatTime } from '../../utils/format';
import { OpenPositionsSkeleton } from './DashboardSkeleton';
import { getMarketContext, isPreMarket, getTodayET } from '../../utils/marketTime';
import { shouldShowEmpty } from '../../utils/testMode';
import type { Position, Trade } from '../../api/types';
import type { SegmentedTabSegment } from '../../components/SegmentedTab';

interface EnrichedPosition extends Position {
  livePrice: number;
  livePnl: number;
  liveR: number;
}

// Exit reason badge helpers
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

function getExitReasonLabel(reason: string | null): string {
  if (!reason) return '—';
  return exitReasonLabels[reason] ?? reason.toUpperCase();
}

function getExitReasonVariant(reason: string | null): 'success' | 'danger' | 'warning' | 'neutral' {
  if (!reason) return 'neutral';
  return exitReasonVariants[reason] ?? 'neutral';
}

type SortField = 'symbol' | 'pnl' | 'r' | 'time';
type SortDir = 'asc' | 'desc';

export function OpenPositions() {
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<EnrichedPosition | null>(null);
  const [sortField, setSortField] = useState<SortField>('time');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const { data: positionsData, isLoading: positionsLoading, error: positionsError } = usePositions();

  // Filter trades to today (ET) to show only "Closed Today"
  const todayET = useMemo(() => getTodayET(), []);
  const { data: tradesData, isLoading: tradesLoading } = useTrades({
    limit: 250,
    date_from: todayET,
    date_to: todayET,
  });
  const priceUpdates = useLiveStore((state) => state.priceUpdates);

  // UI state from Zustand store (persists across layout changes)
  const displayMode = usePositionsUIStore((state) => state.displayMode);
  const setDisplayMode = usePositionsUIStore((state) => state.setDisplayMode);
  const positionFilter = usePositionsUIStore((state) => state.positionFilter);
  const setPositionFilter = usePositionsUIStore((state) => state.setPositionFilter);
  const openSymbolDetail = useSymbolDetailUI((state) => state.open);

  // Extract positions array for stable dependency
  const positions = positionsData?.positions;
  const trades = tradesData?.trades ?? [];
  const closedTotalCount = tradesData?.total_count ?? trades.length;

  // Merge REST positions with WebSocket price updates
  const enrichedPositions = useMemo<EnrichedPosition[]>(() => {
    if (!positions) return [];

    return positions.map((pos) => {
      const wsUpdate = priceUpdates[pos.symbol];

      // Use WebSocket price if available and newer
      const livePrice = wsUpdate?.price ?? pos.current_price;

      // Recalculate P&L with live price
      const priceDiff = pos.side === 'long'
        ? livePrice - pos.entry_price
        : pos.entry_price - livePrice;
      const livePnl = priceDiff * pos.shares_remaining;

      // Recalculate R-multiple with live price
      const stopDiff = Math.abs(pos.entry_price - pos.stop_price);
      const liveR = stopDiff > 0 ? priceDiff / stopDiff : 0;

      return {
        ...pos,
        livePrice,
        livePnl,
        liveR,
      };
    });
  }, [positions, priceUpdates]);

  // Build filter segments with counts
  const filterSegments: SegmentedTabSegment[] = useMemo(() => [
    {
      label: 'All',
      value: 'all',
      count: enrichedPositions.length + closedTotalCount,
    },
    {
      label: 'Open',
      value: 'open',
      count: enrichedPositions.length,
      countVariant: enrichedPositions.length > 0 ? 'success' : undefined,
    },
    {
      label: 'Closed',
      value: 'closed',
      count: closedTotalCount,
    },
  ], [enrichedPositions.length, closedTotalCount]);

  // Toggle sort direction or change field
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  // Sort indicator component
  const SortIndicator = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return <span className="ml-1">{sortDir === 'asc' ? '▲' : '▼'}</span>;
  };

  // Sorted positions
  const sortedPositions = useMemo(() => {
    const sorted = [...enrichedPositions];
    const multiplier = sortDir === 'asc' ? 1 : -1;

    sorted.sort((a, b) => {
      switch (sortField) {
        case 'symbol':
          return multiplier * a.symbol.localeCompare(b.symbol);
        case 'pnl':
          return multiplier * (a.livePnl - b.livePnl);
        case 'r':
          return multiplier * (a.liveR - b.liveR);
        case 'time':
          return multiplier * (a.hold_duration_seconds - b.hold_duration_seconds);
        default:
          return 0;
      }
    });

    return sorted;
  }, [enrichedPositions, sortField, sortDir]);

  // Sorted trades
  const sortedTrades = useMemo(() => {
    const sorted = [...trades];
    const multiplier = sortDir === 'asc' ? 1 : -1;

    sorted.sort((a, b) => {
      switch (sortField) {
        case 'symbol':
          return multiplier * a.symbol.localeCompare(b.symbol);
        case 'pnl':
          return multiplier * ((a.pnl_dollars ?? 0) - (b.pnl_dollars ?? 0));
        case 'r':
          return multiplier * ((a.pnl_r_multiple ?? 0) - (b.pnl_r_multiple ?? 0));
        case 'time':
          // For closed trades, sort by exit_time
          const timeA = a.exit_time ? new Date(a.exit_time).getTime() : 0;
          const timeB = b.exit_time ? new Date(b.exit_time).getTime() : 0;
          return multiplier * (timeA - timeB);
        default:
          return 0;
      }
    });

    return sorted;
  }, [trades, sortField, sortDir]);

  // Handle timeline position/trade click - opens detail panel
  const handleTimelineClick = (item: Position | Trade) => {
    if ('position_id' in item) {
      // It's a Position - find the enriched version and open position detail panel
      const enriched = enrichedPositions.find(p => p.position_id === item.position_id);
      if (enriched) setSelectedPosition(enriched);
      return;
    }
    // It's a Trade
    setSelectedTrade(item);
  };

  // Handle open position row click - opens position detail panel
  const handlePositionRowClick = (position: EnrichedPosition) => {
    setSelectedPosition(position);
  };

  const isLoading = positionFilter === 'closed' ? tradesLoading : positionsLoading;

  if (isLoading) {
    return <OpenPositionsSkeleton />;
  }

  if (positionsError) {
    return (
      <Card>
        <CardHeader title="Positions" />
        <div className="text-argus-loss text-sm">Failed to load positions</div>
      </Card>
    );
  }

  // Test mode: force empty state for testing
  const forceEmpty = shouldShowEmpty('positions');

  // Render all positions view (open + closed combined)
  const renderAllPositions = () => {
    const hasAny = enrichedPositions.length > 0 || trades.length > 0;

    if (!hasAny || forceEmpty) {
      const marketContext = getMarketContext();
      const message = marketContext.status === 'open'
        ? 'No positions today — scanning for setups'
        : 'No positions today';
      return <EmptyState icon={BarChart3} message={message} />;
    }

    // Timeline view - show both open and closed
    if (displayMode === 'timeline') {
      return (
        <div className="p-4 pt-0">
          <PositionTimeline
            positions={enrichedPositions}
            closedTrades={trades}
            onPositionClick={handleTimelineClick}
          />
        </div>
      );
    }

    // Table view - combined table with sections
    return (
      <>
        {/* Desktop/Tablet combined table */}
        <div className="hidden md:block max-h-[420px] overflow-y-auto overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-argus-surface">
              <tr className="bg-argus-surface-2 text-argus-text-dim text-xs uppercase tracking-wider">
                <th
                  className="px-4 py-2 text-left font-medium cursor-pointer hover:text-argus-text select-none w-20"
                  onClick={() => handleSort('symbol')}
                >
                  Symbol<SortIndicator field="symbol" />
                </th>
                <th className="px-4 py-2 text-left font-medium w-28">Strategy</th>
                <th
                  className="px-4 py-2 text-right font-medium cursor-pointer hover:text-argus-text select-none w-20"
                  onClick={() => handleSort('pnl')}
                >
                  P&L<SortIndicator field="pnl" />
                </th>
                <th
                  className="px-4 py-2 text-right font-medium cursor-pointer hover:text-argus-text select-none w-16"
                  onClick={() => handleSort('r')}
                >
                  R<SortIndicator field="r" />
                </th>
                <th className="px-4 py-2 text-center font-medium w-16">Status</th>
                <th className="px-4 py-2 text-center font-medium w-16">Quality</th>
                <th
                  className="px-4 py-2 text-right font-medium cursor-pointer hover:text-argus-text select-none w-20"
                  onClick={() => handleSort('time')}
                >
                  Time<SortIndicator field="time" />
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-argus-border">
              {/* Open positions section */}
              {sortedPositions.length > 0 && (
                <>
                  <tr className="bg-argus-surface-2/50">
                    <td colSpan={7} className="px-4 py-1.5 text-xs font-medium text-argus-accent">
                      Open Positions
                    </td>
                  </tr>
                  {sortedPositions.map((pos) => (
                    <tr
                      key={pos.position_id}
                      className="transition-colors duration-150 hover:bg-argus-bg/50 cursor-pointer"
                      onClick={() => handlePositionRowClick(pos)}
                    >
                      <td className="px-4 py-3 font-medium text-argus-text">
                        <button
                          onClick={(e) => { e.stopPropagation(); openSymbolDetail(pos.symbol); }}
                          className="hover:text-argus-accent hover:underline transition-colors cursor-pointer"
                        >
                          {pos.symbol}
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        <StrategyBadge strategyId={pos.strategy_id} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <PnlValue value={pos.livePnl} size="sm" flash />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <PnlValue value={pos.liveR} format="r-multiple" size="sm" flash />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <Badge variant="success">OPEN</Badge>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-argus-text-dim">—</span>
                      </td>
                      <td className="px-4 py-3 text-right text-argus-text-dim tabular-nums">
                        {formatDuration(pos.hold_duration_seconds)}
                      </td>
                    </tr>
                  ))}
                </>
              )}

              {/* Closed trades section */}
              {trades.length > 0 && (
                <>
                  <tr className="bg-argus-surface-2/50">
                    <td colSpan={7} className="px-4 py-1.5 text-xs font-medium text-argus-text-dim">
                      Closed Today
                    </td>
                  </tr>
                  {sortedTrades.map((trade) => (
                    <tr key={trade.id} className="transition-colors duration-150 hover:bg-argus-bg/50 opacity-75">
                      <td className="px-4 py-3 font-medium text-argus-text">
                        <button
                          onClick={() => openSymbolDetail(trade.symbol)}
                          className="hover:text-argus-accent hover:underline transition-colors cursor-pointer"
                        >
                          {trade.symbol}
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        <StrategyBadge strategyId={trade.strategy_id} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <PnlValue value={trade.pnl_dollars ?? 0} size="sm" />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <PnlValue value={trade.pnl_r_multiple ?? 0} format="r-multiple" size="sm" />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <Badge variant={getExitReasonVariant(trade.exit_reason)}>
                          {getExitReasonLabel(trade.exit_reason)}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <QualityBadge grade={trade.quality_grade ?? ''} score={trade.quality_score ?? undefined} />
                      </td>
                      <td className="px-4 py-3 text-right text-argus-text-dim tabular-nums">
                        {trade.exit_time ? formatTime(trade.exit_time) : '—'}
                      </td>
                    </tr>
                  ))}
                </>
              )}
            </tbody>
          </table>
        </div>

        {/* Phone layout - combined cards */}
        <div className="md:hidden divide-y divide-argus-border">
          {/* Open positions */}
          {enrichedPositions.length > 0 && (
            <>
              <div className="px-4 py-2 bg-argus-surface-2/50">
                <span className="text-xs font-medium text-argus-accent">Open Positions</span>
              </div>
              {sortedPositions.map((pos) => (
                <div
                  key={pos.position_id}
                  className="p-4 transition-colors duration-150 hover:bg-argus-bg/50 cursor-pointer"
                  onClick={() => handlePositionRowClick(pos)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); openSymbolDetail(pos.symbol); }}
                        className="font-medium text-argus-text hover:text-argus-accent hover:underline transition-colors cursor-pointer"
                      >
                        {pos.symbol}
                      </button>
                      <StrategyBadge strategyId={pos.strategy_id} />
                    </div>
                    <PnlValue value={pos.livePnl} size="sm" flash />
                  </div>
                  <div className="flex items-center justify-between mt-1 text-sm">
                    <Badge variant="success">OPEN</Badge>
                    <PnlValue value={pos.liveR} format="r-multiple" size="sm" flash />
                  </div>
                </div>
              ))}
            </>
          )}

          {/* Closed trades */}
          {trades.length > 0 && (
            <>
              <div className="px-4 py-2 bg-argus-surface-2/50">
                <span className="text-xs font-medium text-argus-text-dim">Closed Today</span>
              </div>
              {sortedTrades.map((trade) => (
                <div key={trade.id} className="p-4 transition-colors duration-150 hover:bg-argus-bg/50 opacity-75">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => openSymbolDetail(trade.symbol)}
                        className="font-medium text-argus-text hover:text-argus-accent hover:underline transition-colors cursor-pointer"
                      >
                        {trade.symbol}
                      </button>
                      <StrategyBadge strategyId={trade.strategy_id} />
                    </div>
                    <PnlValue value={trade.pnl_dollars ?? 0} size="sm" />
                  </div>
                  <div className="flex items-center justify-between mt-1 text-sm">
                    <Badge variant={getExitReasonVariant(trade.exit_reason)}>
                      {getExitReasonLabel(trade.exit_reason)}
                    </Badge>
                    <span className="text-argus-text-dim tabular-nums">
                      {trade.exit_time ? formatTime(trade.exit_time) : '—'}
                    </span>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </>
    );
  };

  // Render open positions view
  const renderOpenPositions = () => {
    if (enrichedPositions.length === 0 || forceEmpty) {
      const marketContext = getMarketContext();

      // Select icon and message based on market status
      let icon;
      let message: string;

      switch (marketContext.status) {
        case 'pre_market':
          icon = <Clock className="w-12 h-12 opacity-50" />;
          message = `No open positions — market opens in ${marketContext.timeToOpen ?? 'soon'}`;
          break;
        case 'open':
          // Animated radar icon for active scanning
          icon = (
            <div className="relative w-12 h-12 flex items-center justify-center">
              <Radio className="w-8 h-8 opacity-50" />
              <span className="absolute inset-0 rounded-full border border-argus-accent radar-pulse" />
            </div>
          );
          message = 'No open positions — scanning for setups';
          break;
        case 'after_hours':
        case 'closed':
        default:
          icon = <Moon className="w-12 h-12 opacity-50" />;
          message = 'No open positions — market closed';
          break;
      }

      return <EmptyState icon={icon} message={message} />;
    }

    // Timeline view - show only open positions
    if (displayMode === 'timeline') {
      return (
        <div className="p-4 pt-0">
          <PositionTimeline
            positions={enrichedPositions}
            onPositionClick={handleTimelineClick}
          />
        </div>
      );
    }

    // Table view (default)
    return (
      <>
        {/* Desktop table (lg and up) */}
        <div className="hidden lg:block max-h-[420px] overflow-y-auto overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-argus-surface">
              <tr className="bg-argus-surface-2 text-argus-text-dim text-xs uppercase tracking-wider">
                <th
                  className="px-4 py-2 text-left font-medium cursor-pointer hover:text-argus-text select-none"
                  onClick={() => handleSort('symbol')}
                >
                  Symbol<SortIndicator field="symbol" />
                </th>
                <th className="px-4 py-2 text-left font-medium">Strategy</th>
                <th className="px-4 py-2 text-left font-medium">Side</th>
                <th className="px-4 py-2 text-right font-medium">Entry</th>
                <th className="px-4 py-2 text-right font-medium">Current</th>
                <th
                  className="px-4 py-2 text-right font-medium cursor-pointer hover:text-argus-text select-none"
                  onClick={() => handleSort('pnl')}
                >
                  P&L<SortIndicator field="pnl" />
                </th>
                <th
                  className="px-4 py-2 text-right font-medium cursor-pointer hover:text-argus-text select-none"
                  onClick={() => handleSort('r')}
                >
                  R<SortIndicator field="r" />
                </th>
                <th
                  className="px-4 py-2 text-right font-medium cursor-pointer hover:text-argus-text select-none"
                  onClick={() => handleSort('time')}
                >
                  Time<SortIndicator field="time" />
                </th>
                <th className="px-4 py-2 text-right font-medium">Stop</th>
                <th className="px-4 py-2 text-right font-medium">T1</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-argus-border">
              {sortedPositions.map((pos) => (
                <tr
                  key={pos.position_id}
                  className="transition-colors duration-150 hover:bg-argus-bg/50 cursor-pointer"
                  onClick={() => handlePositionRowClick(pos)}
                >
                  <td className="px-4 py-3 font-medium text-argus-text">
                    <button
                      onClick={(e) => { e.stopPropagation(); openSymbolDetail(pos.symbol); }}
                      className="hover:text-argus-accent hover:underline transition-colors cursor-pointer"
                    >
                      {pos.symbol}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <StrategyBadge strategyId={pos.strategy_id} />
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={pos.side === 'long' ? 'success' : 'danger'}>
                      {pos.side.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">{formatPrice(pos.entry_price)}</td>
                  <td className={`px-4 py-3 text-right tabular-nums ${
                    pos.livePrice > pos.entry_price ? 'text-argus-profit' : pos.livePrice < pos.entry_price ? 'text-argus-loss' : ''
                  }`}>{formatPrice(pos.livePrice)}</td>
                  <td className="px-4 py-3 text-right">
                    <PnlValue value={pos.livePnl} size="sm" flash />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <PnlValue value={pos.liveR} format="r-multiple" size="sm" flash />
                  </td>
                  <td className="px-4 py-3 text-right text-argus-text-dim tabular-nums">
                    {formatDuration(pos.hold_duration_seconds)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-argus-loss">
                    {formatPrice(pos.stop_price)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-argus-profit">
                    {formatPrice(pos.t1_price)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Tablet table (md to lg) */}
        <div className="hidden md:block lg:hidden max-h-[420px] overflow-y-auto overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-argus-surface">
              <tr className="bg-argus-surface-2 text-argus-text-dim text-xs uppercase tracking-wider">
                <th className="px-4 py-2 text-left font-medium">Symbol</th>
                <th className="px-4 py-2 text-right font-medium">Entry</th>
                <th className="px-4 py-2 text-right font-medium">Current</th>
                <th className="px-4 py-2 text-right font-medium">P&L</th>
                <th className="px-4 py-2 text-right font-medium">R</th>
                <th className="px-4 py-2 text-right font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-argus-border">
              {sortedPositions.map((pos) => (
                <tr
                  key={pos.position_id}
                  className="transition-colors duration-150 hover:bg-argus-bg/50 cursor-pointer"
                  onClick={() => handlePositionRowClick(pos)}
                >
                  <td className="px-4 py-3 font-medium text-argus-text">
                    <button
                      onClick={(e) => { e.stopPropagation(); openSymbolDetail(pos.symbol); }}
                      className="hover:text-argus-accent hover:underline transition-colors cursor-pointer"
                    >
                      {pos.symbol}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">{formatPrice(pos.entry_price)}</td>
                  <td className={`px-4 py-3 text-right tabular-nums ${
                    pos.livePrice > pos.entry_price ? 'text-argus-profit' : pos.livePrice < pos.entry_price ? 'text-argus-loss' : ''
                  }`}>{formatPrice(pos.livePrice)}</td>
                  <td className="px-4 py-3 text-right">
                    <PnlValue value={pos.livePnl} size="sm" flash />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <PnlValue value={pos.liveR} format="r-multiple" size="sm" flash />
                  </td>
                  <td className="px-4 py-3 text-right text-argus-text-dim tabular-nums">
                    {formatDuration(pos.hold_duration_seconds)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Phone layout (compact cards) */}
        <div className="md:hidden divide-y divide-argus-border">
          {sortedPositions.map((pos) => (
            <div
              key={pos.position_id}
              className="p-4 transition-colors duration-150 hover:bg-argus-bg/50 cursor-pointer"
              onClick={() => handlePositionRowClick(pos)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => { e.stopPropagation(); openSymbolDetail(pos.symbol); }}
                    className="font-medium text-argus-text hover:text-argus-accent hover:underline transition-colors cursor-pointer"
                  >
                    {pos.symbol}
                  </button>
                  <StrategyBadge strategyId={pos.strategy_id} />
                </div>
                <PnlValue value={pos.livePnl} size="sm" flash />
              </div>
              <div className="flex items-center justify-between mt-1 text-sm">
                <span className="text-argus-text-dim">
                  {pos.side.toUpperCase()} @ {formatPrice(pos.entry_price)}
                </span>
                <PnlValue value={pos.liveR} format="r-multiple" size="sm" flash />
              </div>
            </div>
          ))}
        </div>
      </>
    );
  };

  // Render closed trades view
  const renderClosedTrades = () => {
    if (trades.length === 0) {
      const preMarket = isPreMarket();
      const message = preMarket
        ? 'No trades today — first signal expected after 9:35 AM ET'
        : 'No trades today';

      return <EmptyState icon={BarChart3} message={message} />;
    }

    // Timeline view - show only closed trades
    if (displayMode === 'timeline') {
      return (
        <div className="p-4 pt-0">
          <PositionTimeline
            positions={[]}
            closedTrades={trades}
            onPositionClick={handleTimelineClick}
          />
        </div>
      );
    }

    // Table view
    return (
      <>
        {/* Desktop/Tablet table */}
        <div className="hidden md:block max-h-[420px] overflow-y-auto overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-argus-surface">
              <tr className="bg-argus-surface-2 text-argus-text-dim text-xs uppercase tracking-wider">
                <th
                  className="px-4 py-2 text-left font-medium cursor-pointer hover:text-argus-text select-none w-20"
                  onClick={() => handleSort('symbol')}
                >
                  Symbol<SortIndicator field="symbol" />
                </th>
                <th className="px-4 py-2 text-left font-medium w-28">Strategy</th>
                <th
                  className="px-4 py-2 text-right font-medium cursor-pointer hover:text-argus-text select-none w-20"
                  onClick={() => handleSort('pnl')}
                >
                  P&L<SortIndicator field="pnl" />
                </th>
                <th
                  className="px-4 py-2 text-right font-medium cursor-pointer hover:text-argus-text select-none w-16"
                  onClick={() => handleSort('r')}
                >
                  R<SortIndicator field="r" />
                </th>
                <th className="px-4 py-2 text-center font-medium w-16">Exit</th>
                <th className="px-4 py-2 text-center font-medium w-16">Quality</th>
                <th
                  className="px-4 py-2 text-right font-medium cursor-pointer hover:text-argus-text select-none w-20"
                  onClick={() => handleSort('time')}
                >
                  Time<SortIndicator field="time" />
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-argus-border">
              {sortedTrades.map((trade) => (
                <tr key={trade.id} className="transition-colors duration-150 hover:bg-argus-bg/50">
                  <td className="px-4 py-3 font-medium text-argus-text">
                    <button
                      onClick={() => openSymbolDetail(trade.symbol)}
                      className="hover:text-argus-accent hover:underline transition-colors cursor-pointer"
                    >
                      {trade.symbol}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <StrategyBadge strategyId={trade.strategy_id} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <PnlValue value={trade.pnl_dollars ?? 0} size="sm" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <PnlValue value={trade.pnl_r_multiple ?? 0} format="r-multiple" size="sm" />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge variant={getExitReasonVariant(trade.exit_reason)}>
                      {getExitReasonLabel(trade.exit_reason)}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <QualityBadge grade={trade.quality_grade ?? ''} score={trade.quality_score ?? undefined} />
                  </td>
                  <td className="px-4 py-3 text-right text-argus-text-dim tabular-nums">
                    {trade.exit_time ? formatTime(trade.exit_time) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Phone layout */}
        <div className="md:hidden divide-y divide-argus-border">
          {sortedTrades.map((trade) => (
            <div key={trade.id} className="p-4 transition-colors duration-150 hover:bg-argus-bg/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => openSymbolDetail(trade.symbol)}
                    className="font-medium text-argus-text hover:text-argus-accent hover:underline transition-colors cursor-pointer"
                  >
                    {trade.symbol}
                  </button>
                  <StrategyBadge strategyId={trade.strategy_id} />
                </div>
                <PnlValue value={trade.pnl_dollars ?? 0} size="sm" />
              </div>
              <div className="flex items-center justify-between mt-1 text-sm">
                <Badge variant={getExitReasonVariant(trade.exit_reason)}>
                  {getExitReasonLabel(trade.exit_reason)}
                </Badge>
                <span className="text-argus-text-dim tabular-nums">
                  {trade.exit_time ? formatTime(trade.exit_time) : '—'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </>
    );
  };

  return (
    <>
      <Card noPadding>
        <div className="p-4 pb-0">
          <div className="flex items-start justify-between gap-2">
            <CardHeader
              title="Positions"
              subtitle={
                positionFilter === 'all'
                  ? `${enrichedPositions.length} open, ${trades.length} closed`
                  : positionFilter === 'open'
                  ? `${enrichedPositions.length} open`
                  : `${trades.length} today`
              }
            />

            {/* Display mode toggle - show when there's data in the current filter view */}
            {(positionFilter === 'all'
              ? enrichedPositions.length > 0 || trades.length > 0
              : positionFilter === 'open'
              ? enrichedPositions.length > 0
              : trades.length > 0) && (
              <div className="flex gap-1 p-0.5 bg-argus-surface-2 rounded-md">
                <button
                  onClick={() => setDisplayMode('table')}
                  className={`p-1.5 rounded transition-colors ${
                    displayMode === 'table'
                      ? 'bg-argus-surface text-argus-accent'
                      : 'text-argus-text-dim hover:text-argus-text'
                  }`}
                  aria-label="Table view"
                  title="Table view"
                >
                  <List className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setDisplayMode('timeline')}
                  className={`p-1.5 rounded transition-colors ${
                    displayMode === 'timeline'
                      ? 'bg-argus-surface text-argus-accent'
                      : 'text-argus-text-dim hover:text-argus-text'
                  }`}
                  aria-label="Timeline view"
                  title="Timeline view"
                >
                  <GanttChart className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {/* View filter */}
          <div className="mt-3 mb-2">
            <SegmentedTab
              segments={filterSegments}
              activeValue={positionFilter}
              onChange={(value) => setPositionFilter(value as 'all' | 'open' | 'closed')}
              size="sm"
              layoutId="positions-view-filter"
            />
          </div>
        </div>

        {positionFilter === 'all'
          ? renderAllPositions()
          : positionFilter === 'open'
          ? renderOpenPositions()
          : renderClosedTrades()}
      </Card>

      {/* Trade detail panel - opens when clicking a closed trade on timeline */}
      <TradeDetailPanel
        trade={selectedTrade}
        onClose={() => setSelectedTrade(null)}
      />

      {/* Position detail panel - opens when clicking an open position */}
      <PositionDetailPanel
        position={selectedPosition}
        onClose={() => setSelectedPosition(null)}
      />
    </>
  );
}
