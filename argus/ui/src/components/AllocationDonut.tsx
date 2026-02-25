/**
 * Custom SVG donut visualization for capital allocation with track + fill design.
 *
 * Sprint 18.75 Fix Sessions E + F + G:
 * - Track + fill approach inspired by Apple Watch activity rings
 * - Layer 1: Color-tinted track segments (each tinted with its strategy color)
 * - Layer 2: Bright colored fill arcs for deployed capital (strategies only)
 * - Clear visual hierarchy: each fill arc has a matching colored "container"
 *
 * Design principles:
 * - Primary reading (instant): bright arcs on tinted track = deployment level per strategy
 * - Secondary reading: gaps in track = allocation boundaries
 * - Tertiary reading: center text = exact percentages
 */

import { useState, useEffect, useRef, useMemo, useCallback, memo } from 'react';
import { createPortal } from 'react-dom';
import { motion, animate, AnimatePresence } from 'framer-motion';
import { DURATION } from '../utils/motion';
import { useMediaQuery } from '../hooks/useMediaQuery';

// Strategy color mapping (matches Badge component strategy colors)
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

const RESERVE_COLOR = '#71717a'; // zinc-500 (legend dot)
const CASH_COLOR = '#52525b'; // zinc-600 (matches AllocationBars)

// Get available/unfilled color - matches AllocationBars pattern
function getAvailableColor(color: string): string {
  return `${color}33`; // ~20% opacity (hex suffix)
}

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

// SVG arc path helper - creates an arc path segment
function describeArc(
  cx: number,
  cy: number,
  innerRadius: number,
  outerRadius: number,
  startAngle: number,
  endAngle: number
): string {
  // Convert angles to radians (starting from top, clockwise)
  const startRad = ((startAngle - 90) * Math.PI) / 180;
  const endRad = ((endAngle - 90) * Math.PI) / 180;

  // Calculate points
  const outerStartX = cx + outerRadius * Math.cos(startRad);
  const outerStartY = cy + outerRadius * Math.sin(startRad);
  const outerEndX = cx + outerRadius * Math.cos(endRad);
  const outerEndY = cy + outerRadius * Math.sin(endRad);
  const innerStartX = cx + innerRadius * Math.cos(startRad);
  const innerStartY = cy + innerRadius * Math.sin(startRad);
  const innerEndX = cx + innerRadius * Math.cos(endRad);
  const innerEndY = cy + innerRadius * Math.sin(endRad);

  // Large arc flag (1 if angle > 180 degrees)
  const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;

  // Build path
  return [
    `M ${outerStartX} ${outerStartY}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${outerEndX} ${outerEndY}`,
    `L ${innerEndX} ${innerEndY}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${innerStartX} ${innerStartY}`,
    'Z',
  ].join(' ');
}

// Segment data interface
interface SegmentData {
  id: string;
  name: string;
  color: string;
  trackColor: string; // Precomputed tinted track color
  startAngle: number;
  endAngle: number;
  deployedPct: number; // 0-1, portion of this segment's allocation that is deployed
  isThrottled: boolean;
  isReserve: boolean;
  allocationPct: number; // 0-1, portion of total equity
  allocationDollars: number;
  deployedDollars: number;
}

interface TooltipData {
  name: string;
  allocationDollars: number;
  allocationPct: number;
  deployedDollars: number;
  deployedPct: number;
  isThrottled: boolean;
  isReserve: boolean;
  x: number;
  y: number;
}

export interface Allocation {
  strategy_id: string;
  allocation_pct: number;
  allocation_dollars?: number;
  deployed_pct: number;
  deployed_capital?: number;
  is_throttled: boolean;
}

interface AllocationDonutProps {
  allocations: Allocation[];
  cashReservePct: number;
  totalDeployedPct?: number;
  totalDeployedCapital?: number;
  totalEquity?: number;
  onAnimationComplete?: () => void;
  shouldAnimate?: boolean;
}

// Ring dimensions
const SIZE = 200; // viewBox size
const CX = SIZE / 2;
const CY = SIZE / 2;
const OUTER_RADIUS = 90;
const INNER_RADIUS = 60;
const GAP_DEGREES = 2.5; // Small gap between segments on track


// Custom comparator for React.memo - only re-render if allocation data changes
function arePropsEqual(
  prevProps: AllocationDonutProps,
  nextProps: AllocationDonutProps
): boolean {
  // Compare allocations array by strategy_id and key values
  if (prevProps.allocations.length !== nextProps.allocations.length) return false;
  for (let i = 0; i < prevProps.allocations.length; i++) {
    const prev = prevProps.allocations[i];
    const next = nextProps.allocations[i];
    if (
      prev.strategy_id !== next.strategy_id ||
      prev.allocation_pct !== next.allocation_pct ||
      prev.deployed_pct !== next.deployed_pct ||
      prev.is_throttled !== next.is_throttled
    ) {
      return false;
    }
  }
  // Compare scalar props
  return (
    prevProps.cashReservePct === nextProps.cashReservePct &&
    prevProps.totalDeployedPct === nextProps.totalDeployedPct &&
    prevProps.totalDeployedCapital === nextProps.totalDeployedCapital &&
    prevProps.totalEquity === nextProps.totalEquity &&
    prevProps.shouldAnimate === nextProps.shouldAnimate
  );
}

export const AllocationDonut = memo(function AllocationDonut({
  allocations,
  cashReservePct,
  totalDeployedPct,
  totalDeployedCapital,
  totalEquity = 100000,
  onAnimationComplete,
  shouldAnimate = true,
}: AllocationDonutProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const hasAnimatedRef = useRef(false);

  // Animation state
  const [trackOpacity, setTrackOpacity] = useState(shouldAnimate ? 0 : 1);
  const [fillProgress, setFillProgress] = useState(shouldAnimate ? 0 : 1);
  const [centerOpacity, setCenterOpacity] = useState(shouldAnimate ? 0 : 1);

  const [hoveredSegment, setHoveredSegment] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  // Detect hover capability (desktop only)
  const canHover = useMediaQuery('(hover: hover)');

  // Calculate segment data from allocations with normalization
  const segments = useMemo(() => {
    const segs: SegmentData[] = [];

    // Collect all segments with their raw allocation percentages
    const rawSegments: Array<{
      id: string;
      name: string;
      color: string;
      allocationPct: number;
      allocationDollars: number;
      deployedDollars: number;
      deployedOfAllocation: number;
      isThrottled: boolean;
      isReserve: boolean;
    }> = [];

    // Strategy segments
    allocations.forEach((alloc) => {
      if (alloc.allocation_pct <= 0) return;

      const color = getStrategyColor(alloc.strategy_id);
      const allocationDollars = alloc.allocation_dollars ?? totalEquity * alloc.allocation_pct;
      const deployedDollars = alloc.deployed_capital ?? totalEquity * alloc.deployed_pct;

      // Calculate deployed % relative to this segment's allocation
      const deployedOfAllocation = alloc.allocation_pct > 0
        ? Math.min(1, alloc.deployed_pct / alloc.allocation_pct)
        : 0;

      rawSegments.push({
        id: alloc.strategy_id,
        name: getStrategyDisplayName(alloc.strategy_id),
        color,
        allocationPct: alloc.allocation_pct,
        allocationDollars,
        deployedDollars,
        deployedOfAllocation,
        isThrottled: alloc.is_throttled,
        isReserve: false,
      });
    });

    // Reserve segment
    if (cashReservePct > 0) {
      const reserveDollars = totalEquity * cashReservePct;
      rawSegments.push({
        id: 'reserve',
        name: 'Reserve',
        color: RESERVE_COLOR,
        allocationPct: cashReservePct,
        allocationDollars: reserveDollars,
        deployedDollars: 0,
        deployedOfAllocation: 0,
        isThrottled: false,
        isReserve: true,
      });
    }

    // Calculate total allocation for normalization
    const totalAllocationPct = rawSegments.reduce((sum, s) => sum + s.allocationPct, 0);
    if (totalAllocationPct === 0) return segs;

    // Total gap space needed
    const totalGapDegrees = rawSegments.length * GAP_DEGREES;
    const availableDegrees = 360 - totalGapDegrees;

    // Build segments with normalized angles
    let currentAngle = 0;
    rawSegments.forEach((raw) => {
      // Normalize: each segment gets its share of 360° (minus gaps) proportional to its allocation
      const normalizedPct = raw.allocationPct / totalAllocationPct;
      const angularSpan = normalizedPct * availableDegrees;

      if (angularSpan <= 0) return;

      // Precompute track color - matches AllocationBars "available" colors
      const trackColor = raw.isReserve
        ? getAvailableColor(CASH_COLOR)
        : getAvailableColor(raw.color);

      segs.push({
        id: raw.id,
        name: raw.name,
        color: raw.color,
        trackColor,
        startAngle: currentAngle,
        endAngle: currentAngle + angularSpan,
        deployedPct: raw.deployedOfAllocation,
        isThrottled: raw.isThrottled,
        isReserve: raw.isReserve,
        allocationPct: raw.allocationPct,
        allocationDollars: raw.allocationDollars,
        deployedDollars: raw.deployedDollars,
      });

      // Advance by angular span plus gap
      currentAngle += angularSpan + GAP_DEGREES;
    });

    return segs;
  }, [allocations, cashReservePct, totalEquity]);

  // Calculate total deployed percentage
  const totalDeployed = useMemo(() => {
    if (totalDeployedPct !== undefined) return totalDeployedPct;
    return allocations.reduce((sum, a) => sum + a.deployed_pct, 0);
  }, [allocations, totalDeployedPct]);

  const deployedPctDisplay = Math.round(totalDeployed * 100);

  // Format currency
  const formatDollars = (value: number): string => {
    if (value >= 1000) {
      return `$${(value / 1000).toFixed(1)}k`;
    }
    return `$${value.toFixed(0)}`;
  };

  // Animation sequence: track → fills → marks → center
  useEffect(() => {
    if (!shouldAnimate || hasAnimatedRef.current) return;
    hasAnimatedRef.current = true;

    // Phase 1: Track fades in (200ms)
    const trackControl = animate(0, 1, {
      duration: 0.2,
      ease: 'easeOut',
      onUpdate: setTrackOpacity,
    });

    // Phase 2: After 150ms, fill arcs sweep (400ms with stagger handled in render)
    const fillDelay = setTimeout(() => {
      animate(0, 1, {
        duration: 0.4,
        ease: [0.0, 0.0, 0.2, 1.0], // ease-out
        onUpdate: setFillProgress,
      });
    }, 150);

    // Phase 3: Center text fades in last (150ms)
    const centerDelay = setTimeout(() => {
      animate(0, 1, {
        duration: 0.15,
        ease: 'easeOut',
        onUpdate: setCenterOpacity,
        onComplete: onAnimationComplete,
      });
    }, 550);

    return () => {
      trackControl.stop();
      clearTimeout(fillDelay);
      clearTimeout(centerDelay);
    };
  }, [shouldAnimate, onAnimationComplete]);

  // Snap to final state on window resize
  useEffect(() => {
    const handleResize = () => {
      if (trackOpacity < 1 || fillProgress < 1) {
        setTrackOpacity(1);
        setFillProgress(1);
        setCenterOpacity(1);
        hasAnimatedRef.current = true;
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [trackOpacity, fillProgress]);

  // Handle hover - track mouse position for tooltip
  const handleMouseMove = useCallback((e: React.MouseEvent, segment: SegmentData) => {
    if (!canHover) return;

    setHoveredSegment(segment.id);

    const x = e.clientX;
    const y = e.clientY;

    setTooltip({
      name: segment.name,
      allocationDollars: segment.allocationDollars,
      allocationPct: segment.allocationPct,
      deployedDollars: segment.deployedDollars,
      deployedPct: segment.deployedPct,
      isThrottled: segment.isThrottled,
      isReserve: segment.isReserve,
      x,
      y,
    });
  }, [canHover]);

  const handleMouseEnter = useCallback((segment: SegmentData) => {
    if (!canHover) return;
    setHoveredSegment(segment.id);
  }, [canHover]);

  const handleMouseLeave = useCallback(() => {
    setHoveredSegment(null);
    setTooltip(null);
  }, []);

  // Empty state
  if (segments.length === 0) {
    return (
      <div className="relative aspect-square w-full max-w-[200px] md:max-w-[250px] mx-auto flex items-center justify-center">
        <span className="text-sm text-argus-text-dim text-center px-4">
          No strategies active
        </span>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="relative aspect-square w-full max-w-[200px] md:max-w-[250px] mx-auto">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="w-full h-full"
          style={{ overflow: 'visible' }}
        >
          {/* Layer 1: Color-tinted track segments with gaps */}
          <g style={{ opacity: trackOpacity }}>
            {segments.map((segment) => (
              <path
                key={`track-${segment.id}`}
                d={describeArc(
                  CX,
                  CY,
                  INNER_RADIUS,
                  OUTER_RADIUS,
                  segment.startAngle,
                  segment.endAngle
                )}
                fill={segment.trackColor}
              />
            ))}
          </g>

          {/* Layer 2: Colored Fill Arcs (strategies only, not reserve) */}
          {segments.filter(s => !s.isReserve && s.deployedPct > 0).map((segment, index) => {
            // Calculate segment-specific animation with stagger
            const segmentDelay = index * 0.08;
            const segmentProgress = Math.max(0, Math.min(1,
              (fillProgress - segmentDelay) / (1 - segmentDelay)
            ));

            // Fill arc sweeps from startAngle to deployed portion
            const fillAngularSpan = (segment.endAngle - segment.startAngle) * segment.deployedPct;
            const animatedFillEnd = segment.startAngle + fillAngularSpan * segmentProgress;

            // Don't render if no progress or no deployment
            if (segmentProgress <= 0 || animatedFillEnd <= segment.startAngle) return null;

            // Hover effect
            const isHovered = hoveredSegment === segment.id;
            const scale = isHovered ? 1.03 : 1;
            const filterBrightness = isHovered ? 'brightness(1.15)' : 'brightness(1)';

            return (
              <g
                key={`fill-${segment.id}`}
                style={{
                  transform: `scale(${scale})`,
                  transformOrigin: `${CX}px ${CY}px`,
                  transition: 'transform 0.15s ease-out, filter 0.15s ease-out',
                  filter: filterBrightness,
                  cursor: canHover ? 'pointer' : 'default',
                }}
                onMouseEnter={() => handleMouseEnter(segment)}
                onMouseMove={(e) => handleMouseMove(e, segment)}
                onMouseLeave={handleMouseLeave}
              >
                <path
                  d={describeArc(
                    CX,
                    CY,
                    INNER_RADIUS,
                    OUTER_RADIUS,
                    segment.startAngle,
                    animatedFillEnd
                  )}
                  fill={segment.color}
                />
              </g>
            );
          })}

          {/* Invisible hover targets for all segments (including reserve and unfilled portions) */}
          {segments.map((segment) => (
            <path
              key={`hover-${segment.id}`}
              d={describeArc(
                CX,
                CY,
                INNER_RADIUS,
                OUTER_RADIUS,
                segment.startAngle,
                segment.endAngle
              )}
              fill="transparent"
              style={{ cursor: canHover ? 'pointer' : 'default' }}
              onMouseEnter={() => handleMouseEnter(segment)}
              onMouseMove={(e) => handleMouseMove(e, segment)}
              onMouseLeave={handleMouseLeave}
            />
          ))}
        </svg>

        {/* Center text */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
          style={{ opacity: centerOpacity }}
        >
          <span className="text-3xl font-bold text-argus-text">
            {deployedPctDisplay}%
          </span>
          <span className="text-xs text-argus-text-dim">
            {totalDeployedCapital !== undefined && totalDeployedCapital > 0
              ? `${formatDollars(totalDeployedCapital)} Deployed`
              : 'Deployed'
            }
          </span>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1.5 justify-center text-xs">
        {segments.map((segment) => (
          <div key={segment.id} className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ backgroundColor: segment.color }}
            />
            <span className="text-argus-text-dim">{segment.name}</span>
            {segment.isThrottled && (
              <span className="text-[9px] text-argus-warning">(paused)</span>
            )}
          </div>
        ))}
      </div>

      {/* Tooltip - rendered via Portal to escape parent transforms */}
      {tooltip && canHover && createPortal(
        <AnimatePresence>
          <motion.div
            className="fixed z-50 bg-argus-surface border border-argus-border rounded-lg shadow-xl p-2.5 pointer-events-none"
            style={{
              left: Math.min(tooltip.x + 12, window.innerWidth - 160),
              top: Math.max(tooltip.y - 12, 8),
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: DURATION.fast }}
          >
            <div className="text-xs space-y-1.5 min-w-[140px]">
              <div className="font-medium text-argus-text">{tooltip.name}</div>
              <div className="space-y-0.5 text-argus-text-dim">
                <div className="flex justify-between gap-3">
                  <span>Allocated:</span>
                  <span className="tabular-nums text-argus-text">
                    {formatDollars(tooltip.allocationDollars)} ({Math.round(tooltip.allocationPct * 100)}%)
                  </span>
                </div>
                {!tooltip.isReserve && (
                  <div className="flex justify-between gap-3">
                    <span>Deployed:</span>
                    <span className="tabular-nums text-argus-text">
                      {formatDollars(tooltip.deployedDollars)} ({Math.round(tooltip.deployedPct * 100)}%)
                    </span>
                  </div>
                )}
                <div className="flex justify-between gap-3">
                  <span>Status:</span>
                  <span className={tooltip.isThrottled ? 'text-argus-warning' : 'text-argus-profit'}>
                    {tooltip.isReserve ? 'Reserve' : tooltip.isThrottled ? 'Throttled' : 'Active'}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>,
        document.body
      )}
    </div>
  );
}, arePropsEqual);
