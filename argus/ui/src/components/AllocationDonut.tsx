/**
 * Custom SVG donut visualization for capital allocation with fill levels.
 *
 * Sprint 18.75 Fix Session B:
 * - Single ring with one segment per allocation (strategies + cash reserve)
 * - Each segment has two layers: background (full thickness, desaturated) and
 *   foreground (partial thickness from inner edge, solid) showing deployment level
 * - Sweep animation on mount with staggered segments
 * - Hover tooltips on desktop
 *
 * Design:
 * - Angular width = allocation % of total equity
 * - Fill level = deployed capital as % of allocation (fills from inside-out)
 * - Throttled strategies show gray unfilled portion instead of desaturated color
 */

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
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

const CASH_COLOR = '#71717a'; // zinc-500 (brighter for visibility)
const CASH_DESAT_COLOR = 'rgba(148, 163, 184, 0.35)'; // slate-400 at 35% for visible reserve arc
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

// Creates a desaturated version of a color for unfilled portions
function getDesaturatedColor(color: string, opacity = 0.18): string {
  return `${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')}`;
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
const GAP_DEGREES = 3; // Gap between segments

export function AllocationDonut({
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
  const [animationProgress, setAnimationProgress] = useState(shouldAnimate ? 0 : 1);
  const [centerOpacity, setCenterOpacity] = useState(shouldAnimate ? 0 : 1);
  const [hoveredSegment, setHoveredSegment] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  // Detect hover capability (desktop only)
  const canHover = useMediaQuery('(hover: hover)');

  // Calculate segment data from allocations
  const segments = useMemo(() => {
    const segs: SegmentData[] = [];
    let currentAngle = 0;

    // Strategy segments
    allocations.forEach((alloc) => {
      if (alloc.allocation_pct <= 0) return;

      const color = getStrategyColor(alloc.strategy_id);
      const allocationDollars = alloc.allocation_dollars ?? totalEquity * alloc.allocation_pct;
      const deployedDollars = alloc.deployed_capital ?? totalEquity * alloc.deployed_pct;

      // Calculate angular span (with gap)
      const angularSpan = alloc.allocation_pct * 360 - GAP_DEGREES;
      if (angularSpan <= 0) return;

      // Calculate deployed % relative to this segment's allocation
      const deployedOfAllocation = alloc.allocation_pct > 0
        ? Math.min(1, alloc.deployed_pct / alloc.allocation_pct)
        : 0;

      segs.push({
        id: alloc.strategy_id,
        name: getStrategyDisplayName(alloc.strategy_id),
        color,
        startAngle: currentAngle,
        endAngle: currentAngle + angularSpan,
        deployedPct: deployedOfAllocation,
        isThrottled: alloc.is_throttled,
        isReserve: false,
        allocationPct: alloc.allocation_pct,
        allocationDollars,
        deployedDollars,
      });

      currentAngle += alloc.allocation_pct * 360;
    });

    // Reserve segment
    if (cashReservePct > 0) {
      const angularSpan = cashReservePct * 360 - GAP_DEGREES;
      if (angularSpan > 0) {
        const reserveDollars = totalEquity * cashReservePct;
        segs.push({
          id: 'reserve',
          name: 'Reserve',
          color: CASH_COLOR,
          startAngle: currentAngle,
          endAngle: currentAngle + angularSpan,
          deployedPct: 0,
          isThrottled: false,
          isReserve: true,
          allocationPct: cashReservePct,
          allocationDollars: reserveDollars,
          deployedDollars: 0,
        });
      }
    }

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

  // Sweep animation
  useEffect(() => {
    if (!shouldAnimate || hasAnimatedRef.current) return;
    hasAnimatedRef.current = true;

    // Animate progress from 0 to 1
    const progressControl = animate(0, 1, {
      duration: 0.7,
      ease: [0.0, 0.0, 0.2, 1.0], // ease-out
      onUpdate: setAnimationProgress,
      onComplete: () => {
        // Fade in center text after segments complete
        animate(0, 1, {
          duration: DURATION.normal,
          ease: [0.0, 0.0, 0.2, 1.0],
          onUpdate: setCenterOpacity,
          onComplete: onAnimationComplete,
        });
      },
    });

    return () => progressControl.stop();
  }, [shouldAnimate, onAnimationComplete]);

  // Snap to final state on window resize to prevent broken mid-animation states
  useEffect(() => {
    const handleResize = () => {
      // If animation is in progress (not complete), snap to final state
      if (animationProgress < 1) {
        setAnimationProgress(1);
        setCenterOpacity(1);
        hasAnimatedRef.current = true;
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [animationProgress]);

  // Handle hover - track mouse position for tooltip
  const handleMouseMove = useCallback((e: React.MouseEvent, segment: SegmentData) => {
    if (!canHover) return;

    setHoveredSegment(segment.id);

    // Use mouse position directly with offset
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
          {segments.map((segment, index) => {
            // Calculate segment-specific animation progress
            // Each segment starts slightly after the previous one
            const segmentDelay = index * 0.08;
            const segmentProgress = Math.max(0, Math.min(1,
              (animationProgress - segmentDelay) / (1 - segmentDelay * segments.length / (segments.length - 1 || 1))
            ));

            // Animated end angle
            const animatedEndAngle = segment.startAngle +
              (segment.endAngle - segment.startAngle) * Math.min(1, segmentProgress * 1.2);

            // Fill animation starts after segment sweep is ~60% complete
            const fillProgress = Math.max(0, Math.min(1, (segmentProgress - 0.6) / 0.4));

            // Calculate fill end angle (deployed portion sweeps clockwise along the arc)
            // Fill uses full ring thickness but only covers portion of the angular span
            const segmentAngularSpan = animatedEndAngle - segment.startAngle;
            const fillEndAngle = segment.startAngle + segmentAngularSpan * segment.deployedPct * fillProgress;

            // Unfilled color: gray for throttled, desaturated strategy color otherwise
            const unfilledColor = segment.isReserve
              ? CASH_DESAT_COLOR
              : segment.isThrottled
                ? THROTTLED_COLOR
                : getDesaturatedColor(segment.color, 0.18);

            // Hover effect
            const isHovered = hoveredSegment === segment.id;
            const scale = isHovered ? 1.02 : 1;
            const opacity = isHovered ? 1 : (hoveredSegment ? 0.7 : 1);

            return (
              <g
                key={segment.id}
                style={{
                  transform: `scale(${scale})`,
                  transformOrigin: `${CX}px ${CY}px`,
                  transition: 'transform 0.15s ease-out, opacity 0.15s ease-out',
                  opacity,
                  cursor: canHover ? 'pointer' : 'default',
                }}
                onMouseEnter={() => handleMouseEnter(segment)}
                onMouseMove={(e) => handleMouseMove(e, segment)}
                onMouseLeave={handleMouseLeave}
              >
                {/* Background arc (unfilled portion - full ring thickness) */}
                {animatedEndAngle > segment.startAngle && (
                  <path
                    d={describeArc(
                      CX,
                      CY,
                      INNER_RADIUS,
                      OUTER_RADIUS,
                      segment.startAngle,
                      animatedEndAngle
                    )}
                    fill={unfilledColor}
                  />
                )}

                {/* Foreground arc (deployed portion - sweeps clockwise along arc) */}
                {fillProgress > 0 && segment.deployedPct > 0 && fillEndAngle > segment.startAngle && (
                  <path
                    d={describeArc(
                      CX,
                      CY,
                      INNER_RADIUS,
                      OUTER_RADIUS,
                      segment.startAngle,
                      fillEndAngle
                    )}
                    fill={segment.color}
                  />
                )}
              </g>
            );
          })}
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

      {/* Tooltip - follows cursor with offset */}
      <AnimatePresence>
        {tooltip && canHover && (
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
        )}
      </AnimatePresence>
    </div>
  );
}
