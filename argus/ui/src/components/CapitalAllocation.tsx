/**
 * Capital Allocation visualization with nested two-ring donut chart.
 *
 * Sprint 18.75 Session 2:
 * - Outer ring: Allocation policy (strategy allocations + cash reserve)
 * - Inner ring: Deployment state (deployed vs available capital per strategy)
 * - SegmentedTab toggle between Donut and Bars views
 * - Zustand persistence for view preference
 *
 * Design principles:
 * - Framer Motion animation-once pattern (animate on first mount only)
 * - Recharts nested Pie components for two-ring layout
 * - Responsive: 200px mobile, 250px desktop
 */

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { Card } from './Card';
import { CardHeader } from './CardHeader';
import { SegmentedTab } from './SegmentedTab';
import { DURATION, EASE } from '../utils/motion';
import { useCapitalAllocationUIStore } from '../stores/capitalAllocationUI';

// Strategy color mapping (matches Badge component strategy colors)
const STRATEGY_COLORS: Record<string, string> = {
  orb: '#60a5fa',           // blue-400
  orb_breakout: '#60a5fa',  // blue-400
  scalp: '#c084fc',         // purple-400
  orb_scalp: '#c084fc',     // purple-400
  vwap: '#2dd4bf',          // teal-400
  vwap_reclaim: '#2dd4bf',  // teal-400
  momentum: '#fbbf24',      // amber-400
  afternoon_momentum: '#fbbf24', // amber-400
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
  return STRATEGY_COLORS[normalized] || '#71717a'; // zinc-500 fallback
}

// Creates a desaturated version of a color for "available" portions
function getAvailableColor(color: string): string {
  // Add 20% opacity to create a desaturated/transparent effect
  return `${color}33`; // 33 in hex = ~20% opacity
}

// Chart data types
interface OuterRingEntry {
  name: string;
  value: number;
  color: string;
  strategyId: string | null;
  isCash?: boolean;
}

interface InnerRingEntry {
  name: string;
  value: number;
  color: string;
  isDeployed: boolean;
  isThrottled?: boolean;
  isCash?: boolean;
}

// Props interface matching enriched API data
export interface Allocation {
  strategy_id: string;
  allocation_pct: number;
  allocation_dollars?: number;
  deployed_pct: number;
  deployed_capital?: number;
  is_throttled: boolean;
}

interface CapitalAllocationProps {
  allocations: Allocation[];
  cashReservePct: number;
  totalDeployedPct?: number;
  totalDeployedCapital?: number;
  totalEquity?: number;
}

// View toggle segments
const VIEW_SEGMENTS = [
  { label: 'Donut', value: 'donut' },
  { label: 'Bars', value: 'bars' },
];

// Empty state data for outer ring
const EMPTY_OUTER_DATA: OuterRingEntry[] = [
  { name: 'Empty', value: 100, color: CASH_COLOR, strategyId: null, isCash: true },
];

// Empty state data for inner ring (full ring, same as outer)
const EMPTY_INNER_DATA: InnerRingEntry[] = [
  { name: 'Empty', value: 100, color: CASH_COLOR, isDeployed: false, isCash: true },
];

export function CapitalAllocation({
  allocations,
  cashReservePct,
  totalDeployedPct,
  totalDeployedCapital,
  totalEquity,
}: CapitalAllocationProps) {
  // Track if initial animation has played (use state to be React-idiomatic)
  const [hasAnimated, setHasAnimated] = useState(false);
  useEffect(() => {
    setHasAnimated(true);
  }, []);

  // Zustand view mode
  const viewMode = useCapitalAllocationUIStore((s) => s.viewMode);
  const setViewMode = useCapitalAllocationUIStore((s) => s.setViewMode);

  // Stable key for memoization (prevents Recharts thrashing on reference changes)
  const allocationsKey = JSON.stringify(
    allocations.map((a) => `${a.strategy_id}:${a.allocation_pct}:${a.deployed_pct}:${a.is_throttled}`)
  );

  // Memoize chart data to prevent unnecessary re-renders
  const { outerRingData, innerRingData, totalDeployed } = useMemo(() => {
    const outer: OuterRingEntry[] = [];
    const inner: InnerRingEntry[] = [];
    let deployed = 0;
    let allocated = 0;

    allocations.forEach((alloc) => {
      if (alloc.allocation_pct > 0) {
        const color = getStrategyColor(alloc.strategy_id);
        const allocPctValue = alloc.allocation_pct * 100;

        // Outer ring: full allocation segment
        outer.push({
          name: getStrategyDisplayName(alloc.strategy_id),
          value: allocPctValue,
          color,
          strategyId: alloc.strategy_id,
        });

        // Inner ring: deployed portion + available portion
        // deployed_pct is absolute (0-1 of total equity), need to calculate relative to allocation
        const deployedOfAlloc = alloc.allocation_pct > 0
          ? Math.min(1, alloc.deployed_pct / alloc.allocation_pct)
          : 0;
        const deployedPctValue = allocPctValue * deployedOfAlloc;
        const availablePctValue = allocPctValue * (1 - deployedOfAlloc);

        // Deployed segment
        if (deployedPctValue > 0) {
          inner.push({
            name: `${getStrategyDisplayName(alloc.strategy_id)} Deployed`,
            value: deployedPctValue,
            color,
            isDeployed: true,
          });
        }

        // Available segment (or throttled if throttled)
        if (availablePctValue > 0) {
          inner.push({
            name: `${getStrategyDisplayName(alloc.strategy_id)} Available`,
            value: availablePctValue,
            color: alloc.is_throttled ? THROTTLED_COLOR : getAvailableColor(color),
            isDeployed: false,
            isThrottled: alloc.is_throttled,
          });
        }

        deployed += alloc.deployed_pct;
        allocated += alloc.allocation_pct;
      }
    });

    // Cash reserve segment (outer ring only - inner ring shows as empty)
    const cashPct = cashReservePct * 100;
    if (cashPct > 0) {
      outer.push({
        name: 'Reserve',
        value: cashPct,
        color: CASH_COLOR,
        strategyId: null,
        isCash: true,
      });
      // Inner ring: reserve is always "empty" (not deployed)
      inner.push({
        name: 'Reserve',
        value: cashPct,
        color: getAvailableColor(CASH_COLOR),
        isDeployed: false,
        isCash: true,
      });
    }

    // Unallocated remainder (if any)
    const unallocatedPct = Math.max(0, 100 - (allocated * 100) - cashPct);
    if (unallocatedPct > 0.5) { // Only show if > 0.5%
      outer.push({
        name: 'Unallocated',
        value: unallocatedPct,
        color: '#3f3f46', // zinc-700 (subtle)
        strategyId: null,
      });
      inner.push({
        name: 'Unallocated',
        value: unallocatedPct,
        color: '#3f3f4633', // zinc-700 at 20%
        isDeployed: false,
      });
    }

    return {
      outerRingData: outer,
      innerRingData: inner,
      totalDeployed: totalDeployedPct ?? deployed,
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps -- allocationsKey contains allocations data
  }, [allocationsKey, cashReservePct, totalDeployedPct]);

  const deployedPct = Math.round(totalDeployed * 100);
  const isEmpty = allocations.length === 0;

  // Center display: show deployed % or capital amount
  const centerDisplay = useMemo(() => {
    if (isEmpty) {
      return { primary: '', secondary: 'No strategies active' };
    }
    if (totalDeployedCapital !== undefined && totalEquity !== undefined && totalEquity > 0) {
      const formattedCapital = totalDeployedCapital >= 1000
        ? `$${(totalDeployedCapital / 1000).toFixed(1)}k`
        : `$${totalDeployedCapital.toFixed(0)}`;
      return {
        primary: `${deployedPct}%`,
        secondary: `${formattedCapital} Deployed`,
      };
    }
    return {
      primary: `${deployedPct}%`,
      secondary: 'Deployed',
    };
  }, [isEmpty, deployedPct, totalDeployedCapital, totalEquity]);

  return (
    <Card className="h-full">
      <CardHeader title="Capital Allocation" />

      {/* View toggle */}
      <div className="px-3 pb-2">
        <SegmentedTab
          segments={VIEW_SEGMENTS}
          activeValue={viewMode}
          onChange={(value) => setViewMode(value as 'donut' | 'bars')}
          size="sm"
          layoutId="capital-allocation-view"
        />
      </div>

      {viewMode === 'donut' ? (
        <>
          <motion.div
            initial={hasAnimated ? false : { opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: DURATION.normal, ease: EASE.out }}
            className="relative aspect-square w-full max-w-[200px] md:max-w-[250px] mx-auto"
            style={{ willChange: 'transform' }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                {/* Outer ring - Allocation Policy */}
                <Pie
                  data={isEmpty ? EMPTY_OUTER_DATA : outerRingData}
                  cx="50%"
                  cy="50%"
                  innerRadius="58%"
                  outerRadius="100%"
                  paddingAngle={isEmpty ? 0 : 2}
                  dataKey="value"
                  animationBegin={0}
                  animationDuration={hasAnimated ? 0 : 500}
                  animationEasing="ease-out"
                  isAnimationActive={!hasAnimated}
                >
                  {(isEmpty ? EMPTY_OUTER_DATA : outerRingData).map((entry, index) => (
                    <Cell
                      key={`outer-${index}`}
                      fill={entry.color}
                      stroke="transparent"
                      style={{ cursor: entry.isCash ? 'default' : 'pointer' }}
                    />
                  ))}
                </Pie>

                {/* Inner ring - Deployment State */}
                <Pie
                  data={isEmpty ? EMPTY_INNER_DATA : innerRingData}
                  cx="50%"
                  cy="50%"
                  innerRadius="38%"
                  outerRadius="52%"
                  paddingAngle={0}
                  dataKey="value"
                  animationBegin={hasAnimated ? 0 : 100}
                  animationDuration={hasAnimated ? 0 : 500}
                  animationEasing="ease-out"
                  isAnimationActive={!hasAnimated}
                >
                  {(isEmpty ? EMPTY_INNER_DATA : innerRingData).map((entry, index) => (
                    <Cell
                      key={`inner-${index}`}
                      fill={entry.color}
                      stroke="transparent"
                    />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>

            {/* Center text */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              {isEmpty ? (
                <span className="text-sm text-argus-text-dim text-center px-4">
                  {centerDisplay.secondary}
                </span>
              ) : (
                <>
                  <span className="text-3xl font-bold text-argus-text">
                    {centerDisplay.primary}
                  </span>
                  <span className="text-xs text-argus-text-dim">
                    {centerDisplay.secondary}
                  </span>
                </>
              )}
            </div>
          </motion.div>

          {/* Legend */}
          {!isEmpty && (
            <div className="mt-3 flex flex-wrap gap-2 justify-center text-xs">
              {outerRingData
                .filter((entry) => !entry.isCash && entry.strategyId)
                .map((entry) => (
                  <div key={entry.name} className="flex items-center gap-1">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: entry.color }}
                    />
                    <span className="text-argus-text-dim">{entry.name}</span>
                  </div>
                ))}
              {/* Cash/Reserve legend item */}
              <div className="flex items-center gap-1">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: CASH_COLOR }}
                />
                <span className="text-argus-text-dim">Reserve</span>
              </div>
            </div>
          )}
        </>
      ) : (
        /* Bars view placeholder - Session 3 */
        <div className="flex items-center justify-center h-[200px] md:h-[250px] text-argus-text-dim text-sm">
          Bars view — Session 3
        </div>
      )}
    </Card>
  );
}
