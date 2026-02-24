/**
 * Allocation donut chart showing capital distribution across strategies.
 *
 * UX Feature Backlog item 17-A:
 * - Donut chart with inner radius 60%, outer radius 100%
 * - Segments colored by strategy (uses Badge color mapping)
 * - Cash reserve segment in zinc-700
 * - Center text shows total deployed percentage
 * - Framer Motion entry animation (segments grow from 0)
 * - Responsive: 200px on mobile, 250px on desktop
 */

import { useRef, useEffect, useMemo, memo } from 'react';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { Card } from './Card';
import { CardHeader } from './CardHeader';
import { DURATION, EASE } from '../utils/motion';

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

// Empty state data (full gray donut) - defined at module scope to prevent
// new array reference on every render, which would cause Recharts to rebuild
interface ChartDataEntry {
  name: string;
  value: number;
  color: string;
  isCash?: boolean;
}

const EMPTY_DATA: ChartDataEntry[] = [
  { name: 'Empty', value: 100, color: CASH_COLOR, isCash: true },
];

interface Allocation {
  strategy_id: string;
  allocation_pct: number;
  daily_pnl: number;
}

interface AllocationDonutProps {
  allocations: Allocation[];
  cashReservePct: number;
}

function getStrategyColor(strategyId: string): string {
  const normalized = strategyId.toLowerCase().replace(/-/g, '_');
  return STRATEGY_COLORS[normalized] || '#71717a'; // zinc-500 fallback
}

export const AllocationDonut = memo(function AllocationDonut({ allocations, cashReservePct: _cashReservePct }: AllocationDonutProps) {
  // Track if initial animation has played
  const hasAnimated = useRef(false);
  useEffect(() => {
    hasAnimated.current = true;
  }, []);

  // Memoize chart data to prevent unnecessary re-renders
  const chartData = useMemo(() => {
    const data: ChartDataEntry[] = [];
    let deployed = 0;

    allocations.forEach((alloc) => {
      if (alloc.allocation_pct > 0) {
        data.push({
          name: alloc.strategy_id.toUpperCase().slice(0, 4),
          value: alloc.allocation_pct * 100, // Convert to percentage
          color: getStrategyColor(alloc.strategy_id),
        });
        deployed += alloc.allocation_pct;
      }
    });

    // Add cash reserve segment
    const cashPct = Math.max(0, 1 - deployed);
    if (cashPct > 0) {
      data.push({
        name: 'Cash',
        value: cashPct * 100,
        color: CASH_COLOR,
        isCash: true,
      });
    }

    return { data, totalDeployed: deployed };
  }, [JSON.stringify(allocations.map(a => `${a.strategy_id}:${a.allocation_pct}`))]);

  const deployedPct = Math.round(chartData.totalDeployed * 100);
  const isEmpty = allocations.length === 0;

  return (
    <Card className="h-full">
      <CardHeader title="Capital Allocation" />

      <motion.div
        initial={hasAnimated.current ? false : { opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: DURATION.normal, ease: EASE.out }}
        className="relative aspect-square w-full max-w-[200px] md:max-w-[250px] mx-auto"
        style={{ willChange: 'transform' }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={isEmpty ? EMPTY_DATA : chartData.data}
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="100%"
              paddingAngle={isEmpty ? 0 : 2}
              dataKey="value"
              animationBegin={0}
              animationDuration={hasAnimated.current ? 0 : 500}
              animationEasing="ease-out"
              isAnimationActive={!hasAnimated.current}
            >
              {(isEmpty ? EMPTY_DATA : chartData.data).map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color}
                  stroke="transparent"
                  style={{ cursor: entry.isCash ? 'default' : 'pointer' }}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          {isEmpty ? (
            <span className="text-sm text-argus-text-dim text-center px-4">
              No strategies active
            </span>
          ) : (
            <>
              <span className="text-3xl font-bold text-argus-text">
                {deployedPct}%
              </span>
              <span className="text-xs text-argus-text-dim">Deployed</span>
            </>
          )}
        </div>
      </motion.div>

      {/* Legend */}
      {!isEmpty && (
        <div className="mt-3 flex flex-wrap gap-2 justify-center text-xs">
          {chartData.data.map((entry) => (
            <div key={entry.name} className="flex items-center gap-1">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-argus-text-dim">{entry.name}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
});
