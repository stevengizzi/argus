/**
 * Position Timeline - horizontal visualization of position durations.
 *
 * Displays positions as horizontal bars on a time axis from market open (9:30 AM ET)
 * to market close (4:00 PM ET). Critical for comparing Scalp (30s–5min) vs ORB (5–15min) holds.
 *
 * Sprint 18, Session 11 (18-B from UX Feature Backlog).
 */

import { useMemo, useRef, useEffect, useCallback, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { StrategyBadge } from './Badge';
import { PnlValue } from './PnlValue';
import { formatPrice, formatDuration, formatTime } from '../utils/format';
import { DURATION, EASE } from '../utils/motion';
import { useMediaQuery } from '../hooks/useMediaQuery';
import type { Position, Trade } from '../api/types';

// Market hours in ET (minutes from midnight)
const MARKET_OPEN_MINUTES = 9 * 60 + 30; // 9:30 AM = 570
const MARKET_CLOSE_MINUTES = 16 * 60; // 4:00 PM = 960
const TOTAL_MARKET_MINUTES = MARKET_CLOSE_MINUTES - MARKET_OPEN_MINUTES; // 390 minutes

interface TimelinePosition {
  id: string;
  symbol: string;
  strategyId: string;
  entryTime: Date;
  exitTime: Date | null;
  pnl: number;
  rMultiple: number;
  entryPrice: number;
  holdDurationSeconds: number;
  isOpen: boolean;
  // For time stop indicator
  timeStopMinutes?: number;
}

interface PositionTimelineProps {
  positions: Position[];
  closedTrades?: Trade[];
  onPositionClick?: (position: Position | Trade) => void;
  /** Max minutes to show for time stop indicator. Default: 15 (ORB) */
  defaultTimeStopMinutes?: number;
}

interface TooltipData {
  position: TimelinePosition;
  x: number;
  y: number;
}

/**
 * Get current time in ET minutes from midnight.
 */
function getCurrentETMinutes(): number {
  const now = new Date();
  const etTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  return etTime.getHours() * 60 + etTime.getMinutes();
}

/**
 * Parse ISO timestamp to ET minutes from midnight.
 */
function parseToETMinutes(isoString: string): number {
  const date = new Date(isoString);
  const etTime = new Date(date.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  return etTime.getHours() * 60 + etTime.getMinutes();
}

/**
 * Format minutes to time string.
 * Full format: 570 → "9:30 AM"
 * Abbreviated: 570 → "9:30a", 600 → "10a"
 */
function formatMinutesToTime(minutes: number, abbreviated: boolean = false): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours > 12 ? hours - 12 : hours === 0 ? 12 : hours;

  if (abbreviated) {
    // Abbreviated format: "9a", "10a", "12p", "1p"
    // Include minutes only for non-hour times (e.g., "9:30a")
    const periodChar = period === 'AM' ? 'a' : 'p';
    if (mins === 0) {
      return `${displayHours}${periodChar}`;
    }
    return `${displayHours}:${mins.toString().padStart(2, '0')}${periodChar}`;
  }

  return `${displayHours}:${mins.toString().padStart(2, '0')} ${period}`;
}

/**
 * Get bar color based on P&L.
 */
function getBarColor(pnl: number, isOpen: boolean): string {
  if (!isOpen) {
    // Closed positions are faded
    if (pnl > 0) return 'bg-argus-profit/50';
    if (pnl < 0) return 'bg-argus-loss/50';
    return 'bg-amber-400/50';
  }
  if (pnl > 0) return 'bg-argus-profit';
  if (pnl < 0) return 'bg-argus-loss';
  return 'bg-amber-400'; // Flat or new position
}

export function PositionTimeline({
  positions,
  closedTrades = [],
  onPositionClick,
  defaultTimeStopMinutes = 15,
}: PositionTimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [currentMinutes, setCurrentMinutes] = useState(getCurrentETMinutes());

  // Detect larger screens for responsive time axis labels
  // Below 900px: hourly labels with abbreviated format (e.g., "10a", "11a")
  // 900px and up: 30-minute labels with full format (e.g., "10:00 AM", "10:30 AM")
  const isWideScreen = useMediaQuery('(min-width: 900px)');

  // Update current time every 10 seconds for "now" marker
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMinutes(getCurrentETMinutes());
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll to "now" marker on mount
  useEffect(() => {
    if (containerRef.current) {
      const nowPosition = (currentMinutes - MARKET_OPEN_MINUTES) / TOTAL_MARKET_MINUTES;
      const scrollX = Math.max(0, nowPosition * containerRef.current.scrollWidth - containerRef.current.clientWidth / 2);
      containerRef.current.scrollLeft = scrollX;
    }
  }, [currentMinutes]);

  // Convert positions and trades to timeline format
  const timelinePositions = useMemo<TimelinePosition[]>(() => {
    const result: TimelinePosition[] = [];

    // Open positions
    for (const pos of positions) {
      result.push({
        id: pos.position_id,
        symbol: pos.symbol,
        strategyId: pos.strategy_id,
        entryTime: new Date(pos.entry_time),
        exitTime: null,
        pnl: pos.unrealized_pnl,
        rMultiple: pos.r_multiple_current,
        entryPrice: pos.entry_price,
        holdDurationSeconds: pos.hold_duration_seconds,
        isOpen: true,
        timeStopMinutes: defaultTimeStopMinutes,
      });
    }

    // Closed trades (today only, most recent 10)
    for (const trade of closedTrades.slice(0, 10)) {
      if (!trade.exit_time) continue;
      result.push({
        id: trade.id,
        symbol: trade.symbol,
        strategyId: trade.strategy_id,
        entryTime: new Date(trade.entry_time),
        exitTime: new Date(trade.exit_time),
        pnl: trade.pnl_dollars ?? 0,
        rMultiple: trade.pnl_r_multiple ?? 0,
        entryPrice: trade.entry_price,
        holdDurationSeconds: trade.hold_duration_seconds ?? 0,
        isOpen: false,
      });
    }

    // Sort by entry time
    return result.sort((a, b) => a.entryTime.getTime() - b.entryTime.getTime());
  }, [positions, closedTrades, defaultTimeStopMinutes]);

  // Calculate vertical stacking for overlapping positions
  const stackedPositions = useMemo(() => {
    const lanes: { end: number; items: TimelinePosition[] }[] = [];

    for (const pos of timelinePositions) {
      const startMinutes = parseToETMinutes(pos.entryTime.toISOString());
      const endMinutes = pos.exitTime
        ? parseToETMinutes(pos.exitTime.toISOString())
        : currentMinutes;

      // Find a lane where this position doesn't overlap
      let laneIndex = lanes.findIndex((lane) => lane.end <= startMinutes);
      if (laneIndex === -1) {
        laneIndex = lanes.length;
        lanes.push({ end: endMinutes, items: [] });
      } else {
        lanes[laneIndex].end = Math.max(lanes[laneIndex].end, endMinutes);
      }
      lanes[laneIndex].items.push(pos);
    }

    return lanes;
  }, [timelinePositions, currentMinutes]);

  // Generate time axis labels
  // Desktop: every 30 minutes with full format
  // Mobile: every 60 minutes (hourly) with abbreviated format
  const timeLabels = useMemo(() => {
    const labels: number[] = [];
    const interval = isWideScreen ? 30 : 60;
    // On mobile, start at 10:00 AM (first full hour after open) for cleaner labels
    const startMinutes = isWideScreen ? MARKET_OPEN_MINUTES : 10 * 60;
    for (let m = startMinutes; m <= MARKET_CLOSE_MINUTES; m += interval) {
      labels.push(m);
    }
    return labels;
  }, [isWideScreen]);

  const handleBarHover = useCallback(
    (pos: TimelinePosition, event: React.MouseEvent) => {
      const rect = event.currentTarget.getBoundingClientRect();
      const containerRect = containerRef.current?.getBoundingClientRect();
      if (!containerRect) return;

      setTooltip({
        position: pos,
        x: rect.left - containerRect.left + rect.width / 2,
        y: rect.top - containerRect.top - 8,
      });
    },
    []
  );

  const handleBarLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  const handleBarClick = useCallback(
    (pos: TimelinePosition) => {
      if (!onPositionClick) return;

      // Find the original position or trade
      const original = positions.find((p) => p.position_id === pos.id);
      if (original) {
        onPositionClick(original);
        return;
      }
      const trade = closedTrades.find((t) => t.id === pos.id);
      if (trade) {
        onPositionClick(trade);
      }
    },
    [positions, closedTrades, onPositionClick]
  );

  // Calculate "now" marker position
  const nowPosition = useMemo(() => {
    const clamped = Math.max(MARKET_OPEN_MINUTES, Math.min(MARKET_CLOSE_MINUTES, currentMinutes));
    return ((clamped - MARKET_OPEN_MINUTES) / TOTAL_MARKET_MINUTES) * 100;
  }, [currentMinutes]);

  const isMarketHours = currentMinutes >= MARKET_OPEN_MINUTES && currentMinutes <= MARKET_CLOSE_MINUTES;

  if (timelinePositions.length === 0) {
    return (
      <div className="text-center text-argus-text-dim py-8 text-sm">
        No positions to display on timeline
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Timeline container - horizontally scrollable on mobile */}
      <div
        ref={containerRef}
        className="overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-argus-border scrollbar-track-transparent"
      >
        <div className="min-w-[600px] lg:min-w-0">
          {/* Time axis */}
          <div className="relative h-6 border-b border-argus-border mb-2">
            {timeLabels.map((minutes) => {
              const position = ((minutes - MARKET_OPEN_MINUTES) / TOTAL_MARKET_MINUTES) * 100;
              return (
                <div
                  key={minutes}
                  className="absolute transform -translate-x-1/2 text-xs text-argus-text-dim whitespace-nowrap"
                  style={{ left: `${position}%` }}
                >
                  <div className="h-2 w-px bg-argus-border mx-auto mb-0.5" />
                  {formatMinutesToTime(minutes, !isWideScreen)}
                </div>
              );
            })}

            {/* "Now" marker */}
            {isMarketHours && (
              <motion.div
                className="absolute top-0 bottom-0 w-0.5 bg-argus-accent z-10"
                style={{ left: `${nowPosition}%` }}
                initial={{ opacity: 0, scaleY: 0 }}
                animate={{ opacity: 1, scaleY: 1 }}
                transition={{ duration: DURATION.normal, ease: EASE.out }}
              >
                <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-argus-accent rounded-full" />
              </motion.div>
            )}
          </div>

          {/* Position bars */}
          <div className="relative" style={{ minHeight: `${Math.max(1, stackedPositions.length) * 36}px` }}>
            <AnimatePresence mode="popLayout">
              {stackedPositions.map((lane, laneIndex) =>
                lane.items.map((pos) => {
                  const entryMinutes = parseToETMinutes(pos.entryTime.toISOString());
                  const endMinutes = pos.exitTime
                    ? parseToETMinutes(pos.exitTime.toISOString())
                    : currentMinutes;

                  const left = ((entryMinutes - MARKET_OPEN_MINUTES) / TOTAL_MARKET_MINUTES) * 100;
                  const width = ((endMinutes - entryMinutes) / TOTAL_MARKET_MINUTES) * 100;

                  // Time stop indicator position (only for open positions)
                  const timeStopPosition = pos.isOpen && pos.timeStopMinutes
                    ? ((entryMinutes + pos.timeStopMinutes - MARKET_OPEN_MINUTES) / TOTAL_MARKET_MINUTES) * 100
                    : null;

                  return (
                    <motion.div
                      key={pos.id}
                      layout
                      className={`absolute h-7 rounded-md cursor-pointer transition-shadow hover:shadow-lg hover:z-20 flex items-center gap-1 px-1.5 overflow-hidden ${getBarColor(pos.pnl, pos.isOpen)}`}
                      style={{
                        left: `${left}%`,
                        width: `max(${width}%, 48px)`, // Minimum width for visibility
                        top: `${laneIndex * 36}px`,
                      }}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{
                        opacity: pos.isOpen ? 1 : 0.6,
                        x: 0,
                        width: `max(${width}%, 48px)`,
                      }}
                      exit={{ opacity: 0, transition: { duration: DURATION.slow } }}
                      transition={{
                        layout: { type: 'spring', stiffness: 300, damping: 30 },
                        opacity: { duration: pos.isOpen ? DURATION.normal : 2 },
                      }}
                      onMouseEnter={(e) => handleBarHover(pos, e)}
                      onMouseLeave={handleBarLeave}
                      onClick={() => handleBarClick(pos)}
                    >
                      {/* Symbol */}
                      <span className="text-xs font-medium text-white truncate">
                        {pos.symbol}
                      </span>

                      {/* Strategy badge (only if there's room) */}
                      {width > 8 && (
                        <span className="hidden sm:inline-flex">
                          <StrategyBadge strategyId={pos.strategyId} onAmber={pos.pnl === 0} />
                        </span>
                      )}

                      {/* Time stop indicator */}
                      {timeStopPosition !== null && timeStopPosition > left && timeStopPosition < 100 && (
                        <div
                          className="absolute top-0 bottom-0 w-px border-l border-dashed border-white/40"
                          style={{ left: `${((timeStopPosition - left) / width) * 100}%` }}
                        />
                      )}
                    </motion.div>
                  );
                })
              )}
            </AnimatePresence>

            {/* "Now" line extending through bars */}
            {isMarketHours && (
              <div
                className="absolute top-0 bottom-0 w-px bg-argus-accent/30 pointer-events-none"
                style={{ left: `${nowPosition}%` }}
              />
            )}
          </div>
        </div>
      </div>

      {/* Tooltip */}
      <AnimatePresence>
        {tooltip && (
          <motion.div
            className="absolute z-30 bg-argus-surface border border-argus-border rounded-lg shadow-xl p-3 pointer-events-none min-w-[180px]"
            style={{
              left: `${Math.min(Math.max(tooltip.x, 90), containerRef.current?.clientWidth ? containerRef.current.clientWidth - 90 : 1000)}px`,
              top: `${tooltip.y - 8}px`,
              transform: 'translate(-50%, -100%)',
            }}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: DURATION.fast }}
          >
            {/* Arrow */}
            <div className="absolute left-1/2 -translate-x-1/2 bottom-0 translate-y-full w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[6px] border-t-argus-border" />

            <div className="space-y-2">
              {/* Header */}
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium text-argus-text">{tooltip.position.symbol}</span>
                <StrategyBadge strategyId={tooltip.position.strategyId} />
              </div>

              {/* Details grid */}
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                <span className="text-argus-text-dim">Entry</span>
                <span className="text-right tabular-nums">{formatPrice(tooltip.position.entryPrice)}</span>

                <span className="text-argus-text-dim">P&L</span>
                <span className="text-right">
                  <PnlValue value={tooltip.position.pnl} size="sm" />
                </span>

                <span className="text-argus-text-dim">R-Multiple</span>
                <span className="text-right">
                  <PnlValue value={tooltip.position.rMultiple} format="r-multiple" size="sm" />
                </span>

                <span className="text-argus-text-dim">Duration</span>
                <span className="text-right tabular-nums">
                  {formatDuration(tooltip.position.holdDurationSeconds)}
                </span>

                <span className="text-argus-text-dim">Entry Time</span>
                <span className="text-right tabular-nums">
                  {formatTime(tooltip.position.entryTime.toISOString())}
                </span>
              </div>

              {/* Status */}
              <div className="text-xs text-center pt-1 border-t border-argus-border">
                {tooltip.position.isOpen ? (
                  <span className="text-argus-accent">Open Position</span>
                ) : (
                  <span className="text-argus-text-dim">Closed</span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
