/**
 * Horizontal stacked bars visualization for capital allocation.
 *
 * Sprint 18.75 Session 3, Fix Session A:
 * - One bar per strategy + reserve
 * - Each bar shows: deployed (solid), available (desaturated), throttled (gray)
 * - Consistent layout at all breakpoints: label above, bar full width, values below
 * - Hover tooltips on desktop
 * - Staggered animation on mount
 */

import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { staggerContainer, staggerItem, DURATION, EASE } from '../utils/motion';
import { useMediaQuery } from '../hooks/useMediaQuery';

// Strategy color mapping (matches CapitalAllocation)
const STRATEGY_COLORS: Record<string, string> = {
  orb: '#60a5fa',           // blue-400
  orb_breakout: '#60a5fa',
  scalp: '#c084fc',         // purple-400
  orb_scalp: '#c084fc',
  vwap: '#2dd4bf',          // teal-400
  vwap_reclaim: '#2dd4bf',
  momentum: '#fbbf24',      // amber-400
  afternoon_momentum: '#fbbf24',
};

const CASH_COLOR = '#52525b'; // zinc-600
const THROTTLED_COLOR = '#71717a'; // zinc-500

// Display names for strategies
const STRATEGY_DISPLAY_NAMES: Record<string, string> = {
  orb: 'ORB',
  orb_breakout: 'ORB Breakout',
  scalp: 'Scalp',
  orb_scalp: 'ORB Scalp',
  vwap: 'VWAP',
  vwap_reclaim: 'VWAP Reclaim',
  momentum: 'Momentum',
  afternoon_momentum: 'Afternoon Mom',
};

function getStrategyDisplayName(strategyId: string): string {
  const normalized = strategyId.toLowerCase().replace(/-/g, '_');
  return STRATEGY_DISPLAY_NAMES[normalized] || strategyId;
}

function getStrategyColor(strategyId: string): string {
  const normalized = strategyId.toLowerCase().replace(/-/g, '_');
  return STRATEGY_COLORS[normalized] || '#71717a';
}

function getAvailableColor(color: string): string {
  return `${color}33`; // ~20% opacity
}

function formatDollars(value: number): string {
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}k`;
  }
  return `$${value.toFixed(0)}`;
}

export interface AllocationBarData {
  strategy_id: string;
  allocation_pct: number;
  allocation_dollars?: number;
  deployed_pct: number;
  deployed_capital?: number;
  is_throttled: boolean;
}

interface AllocationBarsProps {
  allocations: AllocationBarData[];
  cashReservePct: number;
  totalEquity?: number;
}

interface TooltipData {
  strategyId: string;
  name: string;
  segment: 'deployed' | 'available' | 'reserve';
  value: number;
  pct: number;
  x: number;
  y: number;
}

export function AllocationBars({
  allocations,
  cashReservePct,
  totalEquity = 100000,
}: AllocationBarsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [hasAnimated, setHasAnimated] = useState(false);
  const [containerWidth, setContainerWidth] = useState(1000);

  // Detect hover capability (desktop only)
  const canHover = useMediaQuery('(hover: hover)');

  // Track container width for tooltip positioning
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth);
      }
    };
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  // Mark as animated after first render
  useEffect(() => {
    const timer = setTimeout(() => setHasAnimated(true), 600);
    return () => clearTimeout(timer);
  }, []);

  // Calculate bar data with proper widths
  const barData = useMemo(() => {
    const bars: Array<{
      id: string;
      name: string;
      color: string;
      allocationPct: number;
      allocationDollars: number;
      deployedPct: number;
      deployedDollars: number;
      availableDollars: number;
      isThrottled: boolean;
      isReserve: boolean;
    }> = [];

    // Strategy bars
    allocations.forEach((alloc) => {
      if (alloc.allocation_pct <= 0) return;

      const color = getStrategyColor(alloc.strategy_id);
      const allocationDollars = alloc.allocation_dollars ?? totalEquity * alloc.allocation_pct;
      const deployedDollars = alloc.deployed_capital ?? totalEquity * alloc.deployed_pct;
      const availableDollars = allocationDollars - deployedDollars;

      // Calculate deployed % relative to this strategy's allocation
      const deployedOfAllocation = alloc.allocation_pct > 0
        ? Math.min(1, alloc.deployed_pct / alloc.allocation_pct)
        : 0;

      bars.push({
        id: alloc.strategy_id,
        name: getStrategyDisplayName(alloc.strategy_id),
        color,
        allocationPct: alloc.allocation_pct * 100,
        allocationDollars,
        deployedPct: deployedOfAllocation * 100,
        deployedDollars,
        availableDollars: Math.max(0, availableDollars),
        isThrottled: alloc.is_throttled,
        isReserve: false,
      });
    });

    // Reserve bar (always at bottom)
    if (cashReservePct > 0) {
      const reserveDollars = totalEquity * cashReservePct;
      bars.push({
        id: 'reserve',
        name: 'Reserve',
        color: CASH_COLOR,
        allocationPct: cashReservePct * 100,
        allocationDollars: reserveDollars,
        deployedPct: 0,
        deployedDollars: 0,
        availableDollars: reserveDollars,
        isThrottled: false,
        isReserve: true,
      });
    }

    return bars;
  }, [allocations, cashReservePct, totalEquity]);


  const handleSegmentHover = useCallback(
    (
      bar: (typeof barData)[0],
      segment: 'deployed' | 'available' | 'reserve',
      event: React.MouseEvent
    ) => {
      const rect = event.currentTarget.getBoundingClientRect();
      const containerRect = containerRef.current?.getBoundingClientRect();
      if (!containerRect) return;

      let value = 0;
      let pct = 0;

      if (segment === 'deployed') {
        value = bar.deployedDollars;
        pct = bar.deployedPct;
      } else if (segment === 'available' || segment === 'reserve') {
        value = bar.availableDollars;
        pct = 100 - bar.deployedPct;
      }

      setTooltip({
        strategyId: bar.id,
        name: bar.name,
        segment,
        value,
        pct,
        x: rect.left - containerRect.left + rect.width / 2,
        y: rect.top - containerRect.top,
      });
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  if (barData.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] md:h-[250px] text-argus-text-dim text-sm">
        No strategies registered
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative px-3 pb-3">
      <motion.div
        variants={staggerContainer(0.1)}
        initial="hidden"
        animate="show"
        className="space-y-3"
      >
        {barData.map((bar) => (
          <motion.div
            key={bar.id}
            variants={staggerItem}
            className="space-y-1.5"
          >
            {/* Strategy name above bar (all breakpoints) */}
            <div className="flex items-center gap-2">
              <span
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: bar.color }}
              />
              <span className="text-sm font-medium text-argus-text truncate">
                {bar.name}
              </span>
              {bar.isThrottled && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-argus-warning/20 text-argus-warning font-medium">
                  Paused
                </span>
              )}
            </div>

            {/* Bar (full width, all breakpoints) */}
            <div
              className="h-6 rounded overflow-hidden flex"
              style={{
                width: '100%',
              }}
            >
              {/* Deployed segment */}
              {bar.deployedPct > 0 && (
                <motion.div
                  className="h-full cursor-default"
                  style={{ backgroundColor: bar.color }}
                  initial={hasAnimated ? false : { width: 0 }}
                  animate={{ width: `${bar.deployedPct}%` }}
                  transition={{
                    duration: hasAnimated ? DURATION.normal : DURATION.slow,
                    ease: EASE.out,
                  }}
                  onMouseEnter={(e) => handleSegmentHover(bar, 'deployed', e)}
                  onMouseLeave={handleMouseLeave}
                />
              )}

              {/* Available or Throttled segment */}
              {bar.deployedPct < 100 && (
                <motion.div
                  className="h-full cursor-default"
                  style={{
                    backgroundColor: bar.isReserve
                      ? getAvailableColor(CASH_COLOR)
                      : bar.isThrottled
                        ? THROTTLED_COLOR
                        : getAvailableColor(bar.color),
                  }}
                  initial={hasAnimated ? false : { width: 0 }}
                  animate={{ width: `${100 - bar.deployedPct}%` }}
                  transition={{
                    duration: hasAnimated ? DURATION.normal : DURATION.slow,
                    ease: EASE.out,
                    delay: hasAnimated ? 0 : 0.1,
                  }}
                  onMouseEnter={(e) =>
                    handleSegmentHover(bar, bar.isReserve ? 'reserve' : 'available', e)
                  }
                  onMouseLeave={handleMouseLeave}
                />
              )}
            </div>

            {/* Values below bar (all breakpoints) */}
            <div className="flex items-center justify-between text-xs">
              <span className="text-argus-text-dim tabular-nums">
                {formatDollars(bar.deployedDollars)} / {formatDollars(bar.allocationDollars)} deployed
              </span>
              <span className="text-argus-text tabular-nums font-medium">
                {Math.round(bar.deployedPct)}%
              </span>
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* Tooltip (desktop only) */}
      <AnimatePresence>
        {tooltip && canHover && (
          <motion.div
            className="absolute z-30 bg-argus-surface border border-argus-border rounded-lg shadow-xl p-2.5 pointer-events-none"
            style={{
              left: Math.min(Math.max(tooltip.x, 70), containerWidth - 70),
              top: tooltip.y - 8,
              transform: 'translate(-50%, -100%)',
            }}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: DURATION.fast }}
          >
            {/* Arrow */}
            <div className="absolute left-1/2 -translate-x-1/2 bottom-0 translate-y-full w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[6px] border-t-argus-border" />

            <div className="text-xs space-y-1">
              <div className="font-medium text-argus-text">{tooltip.name}</div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-argus-text-dim capitalize">{tooltip.segment}</span>
                <span className="tabular-nums text-argus-text">
                  {formatDollars(tooltip.value)} ({Math.round(tooltip.pct)}%)
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Legend */}
      <div className="mt-4 pt-3 border-t border-argus-border">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-argus-text-dim">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 rounded-sm bg-blue-400" />
            <span>Deployed</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 rounded-sm bg-blue-400/20" />
            <span>Available</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 rounded-sm" style={{ backgroundColor: THROTTLED_COLOR }} />
            <span>Throttled</span>
          </div>
        </div>
      </div>
    </div>
  );
}
