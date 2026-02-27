/**
 * Capital Allocation visualization with custom SVG donut and stacked bars.
 *
 * Sprint 18.75 Fix Session B:
 * - Donut view: Single ring with fill-level segments (deployed fills from inside-out)
 * - Bars view: Horizontal stacked bars with deployed/available/throttled segments
 * - SegmentedTab toggle between views with AnimatePresence crossfade
 * - Zustand persistence for view preference
 *
 * Design principles:
 * - Custom SVG donut replaces Recharts nested rings
 * - Framer Motion sweep animation on mount and view toggle
 * - Animation-once pattern per view (animate on first mount only)
 */

import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card } from './Card';
import { CardHeader } from './CardHeader';
import { SegmentedTab } from './SegmentedTab';
import { AllocationDonut } from './AllocationDonut';
import { AllocationBars } from './AllocationBars';
import { DURATION, EASE, quickFade } from '../utils/motion';
import { useCapitalAllocationUIStore } from '../stores/capitalAllocationUI';

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

export function CapitalAllocation({
  allocations,
  cashReservePct,
  totalDeployedPct,
  totalDeployedCapital,
  totalEquity,
}: CapitalAllocationProps) {
  // Track animation keys for fresh animations when switching views
  const donutAnimatedRef = useRef(false);
  const [donutKey, setDonutKey] = useState(0);
  const [barsKey, setBarsKey] = useState(0);

  // Zustand view mode
  const viewMode = useCapitalAllocationUIStore((s) => s.viewMode);
  const setViewMode = useCapitalAllocationUIStore((s) => s.setViewMode);

  // Handle view change - increment key to trigger fresh animation
  const handleViewChange = useCallback((value: string) => {
    const newMode = value as 'donut' | 'bars';
    if (newMode === 'donut') {
      setDonutKey((k) => k + 1);
    } else {
      setBarsKey((k) => k + 1);
    }
    setViewMode(newMode);
  }, [setViewMode]);

  const isEmpty = allocations.length === 0;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader title="Capital Allocation" />

      {/* View toggle */}
      <div className="px-3 pb-2">
        <SegmentedTab
          segments={VIEW_SEGMENTS}
          activeValue={viewMode}
          onChange={handleViewChange}
          size="sm"
          layoutId="capital-allocation-view"
        />
      </div>

      {/* Content area - flex-1 to fill height, centered content, min-h for standalone use */}
      <div className="flex-1 min-h-[280px] md:min-h-[320px] flex flex-col justify-center">
        <AnimatePresence mode="wait">
          {viewMode === 'donut' ? (
            <motion.div
              key={`donut-view-${donutKey}`}
              variants={quickFade}
              initial="hidden"
              animate="show"
              exit="hidden"
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: DURATION.normal, ease: EASE.out }}
                className="py-2"
                style={{ willChange: 'transform' }}
              >
                {isEmpty ? (
                  <div className="relative aspect-square w-full max-w-[200px] md:max-w-[250px] mx-auto flex items-center justify-center">
                    <span className="text-sm text-argus-text-dim text-center px-4">
                      No strategies active
                    </span>
                  </div>
                ) : (
                  <AllocationDonut
                    allocations={allocations}
                    cashReservePct={cashReservePct}
                    totalDeployedPct={totalDeployedPct}
                    totalDeployedCapital={totalDeployedCapital}
                    totalEquity={totalEquity}
                    shouldAnimate={true}
                    onAnimationComplete={() => {
                      donutAnimatedRef.current = true;
                    }}
                  />
                )}
              </motion.div>
            </motion.div>
          ) : (
            <motion.div
              key={`bars-view-${barsKey}`}
              variants={quickFade}
              initial="hidden"
              animate="show"
              exit="hidden"
            >
              <AllocationBars
                key={barsKey}
                allocations={allocations}
                cashReservePct={cashReservePct}
                totalEquity={totalEquity}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  );
}
