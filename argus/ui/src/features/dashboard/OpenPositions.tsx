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
import { SegmentedTab } from '../../components/SegmentedTab';
import { PositionTimeline } from '../../components/PositionTimeline';
import { TradeDetailPanel } from '../trades/TradeDetailPanel';
import { usePositions } from '../../hooks/usePositions';
import { useTrades } from '../../hooks/useTrades';
import { useLiveStore } from '../../stores/live';
import { formatPrice, formatDuration, formatTime } from '../../utils/format';
import { OpenPositionsSkeleton } from './DashboardSkeleton';
import { getMarketContext, isPreMarket } from '../../utils/marketTime';
import { shouldShowEmpty } from '../../utils/testMode';
import type { Position, Trade } from '../../api/types';
import type { SegmentedTabSegment } from '../../components/SegmentedTab';

interface EnrichedPosition extends Position {
  livePrice: number;
  livePnl: number;
  liveR: number;
}

type ViewFilter = 'open' | 'closed';
type DisplayMode = 'table' | 'timeline';

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

export function OpenPositions() {
  const [viewFilter, setViewFilter] = useState<ViewFilter>('open');
  const [displayMode, setDisplayMode] = useState<DisplayMode>('table');
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const { data: positionsData, isLoading: positionsLoading, error: positionsError } = usePositions();
  const { data: tradesData, isLoading: tradesLoading } = useTrades({ limit: 10 });
  const priceUpdates = useLiveStore((state) => state.priceUpdates);

  // Extract positions array for stable dependency
  const positions = positionsData?.positions;
  const trades = tradesData?.trades ?? [];

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
      label: 'Open',
      value: 'open',
      count: enrichedPositions.length,
      countVariant: enrichedPositions.length > 0 ? 'success' : undefined,
    },
    {
      label: 'Closed',
      value: 'closed',
      count: trades.length,
    },
  ], [enrichedPositions.length, trades.length]);

  // Handle timeline position/trade click - opens detail panel
  const handleTimelineClick = (item: Position | Trade) => {
    // Convert Position to Trade format for the panel
    // The panel expects a Trade, so we create a minimal trade-like object
    if ('position_id' in item) {
      // It's a Position - we can't open the detail panel for open positions yet
      // TODO: Create a PositionDetailPanel for open positions
      return;
    }
    // It's a Trade
    setSelectedTrade(item);
  };

  const isLoading = viewFilter === 'open' ? positionsLoading : tradesLoading;

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

    // Timeline view
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

    // Table view (default)
    return (
      <>
        {/* Desktop table (lg and up) */}
        <div className="hidden lg:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-argus-surface-2 text-argus-text-dim text-xs uppercase tracking-wider">
                <th className="px-4 py-2 text-left font-medium">Symbol</th>
                <th className="px-4 py-2 text-left font-medium">Strategy</th>
                <th className="px-4 py-2 text-left font-medium">Side</th>
                <th className="px-4 py-2 text-right font-medium">Entry</th>
                <th className="px-4 py-2 text-right font-medium">Current</th>
                <th className="px-4 py-2 text-right font-medium">P&L</th>
                <th className="px-4 py-2 text-right font-medium">R</th>
                <th className="px-4 py-2 text-right font-medium">Time</th>
                <th className="px-4 py-2 text-right font-medium">Stop</th>
                <th className="px-4 py-2 text-right font-medium">T1</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-argus-border">
              {enrichedPositions.map((pos) => (
                <tr key={pos.position_id} className="transition-colors duration-150 hover:bg-argus-bg/50">
                  <td className="px-4 py-3 font-medium text-argus-text">{pos.symbol}</td>
                  <td className="px-4 py-3">
                    <StrategyBadge strategyId={pos.strategy_id} />
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={pos.side === 'long' ? 'success' : 'danger'}>
                      {pos.side.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">{formatPrice(pos.entry_price)}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{formatPrice(pos.livePrice)}</td>
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
        <div className="hidden md:block lg:hidden overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
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
              {enrichedPositions.map((pos) => (
                <tr key={pos.position_id} className="transition-colors duration-150 hover:bg-argus-bg/50">
                  <td className="px-4 py-3 font-medium text-argus-text">{pos.symbol}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{formatPrice(pos.entry_price)}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{formatPrice(pos.livePrice)}</td>
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
          {enrichedPositions.map((pos) => (
            <div key={pos.position_id} className="p-4 transition-colors duration-150 hover:bg-argus-bg/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-argus-text">{pos.symbol}</span>
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

    return (
      <>
        {/* Desktop/Tablet table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-argus-surface-2 text-argus-text-dim text-xs uppercase tracking-wider">
                <th className="px-4 py-2 text-left font-medium">Symbol</th>
                <th className="px-4 py-2 text-left font-medium">Strategy</th>
                <th className="px-4 py-2 text-right font-medium">P&L</th>
                <th className="px-4 py-2 text-right font-medium">R</th>
                <th className="px-4 py-2 text-center font-medium">Exit</th>
                <th className="px-4 py-2 text-right font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-argus-border">
              {trades.map((trade) => (
                <tr key={trade.id} className="transition-colors duration-150 hover:bg-argus-bg/50">
                  <td className="px-4 py-3 font-medium text-argus-text">{trade.symbol}</td>
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
          {trades.map((trade) => (
            <div key={trade.id} className="p-4 transition-colors duration-150 hover:bg-argus-bg/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-argus-text">{trade.symbol}</span>
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
              subtitle={viewFilter === 'open'
                ? `${enrichedPositions.length} open`
                : `${trades.length} today`
              }
            />

            {/* Display mode toggle - only show when there are positions and on tablet+ */}
            {viewFilter === 'open' && enrichedPositions.length > 0 && (
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
              activeValue={viewFilter}
              onChange={(value) => setViewFilter(value as ViewFilter)}
              size="sm"
              layoutId="positions-view-filter"
            />
          </div>
        </div>

        {viewFilter === 'open' ? renderOpenPositions() : renderClosedTrades()}
      </Card>

      {/* Trade detail panel - opens when clicking a closed trade on timeline */}
      <TradeDetailPanel
        trade={selectedTrade}
        onClose={() => setSelectedTrade(null)}
      />
    </>
  );
}
