/**
 * R-Multiple Distribution Histogram.
 *
 * Shows trade outcomes distributed by R-multiple in histogram form.
 * Features:
 * - Recharts BarChart with red (negative) / green (positive) bar colors
 * - 0R and mean R vertical reference lines
 * - Strategy filter dropdown
 * - Hover tooltip: bin range, count, % of total, avg P&L
 * - Mean/Median annotation below chart
 * - Responsive sizing
 */

import { useState, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card } from '../../components/Card';
import { useDistribution } from '../../hooks/useDistribution';
import type { PerformancePeriod } from '../../api/types';

// Strategy options for filter
const STRATEGY_OPTIONS = [
  { label: 'All Strategies', value: 'all' },
  { label: 'ORB Breakout', value: 'strat_orb_breakout' },
  { label: 'ORB Scalp', value: 'strat_orb_scalp' },
  { label: 'VWAP Reclaim', value: 'strat_vwap_reclaim' },
  { label: 'Afternoon Momentum', value: 'strat_afternoon_momentum' },
];

// Colors
const PROFIT_COLOR = '#22c55e';
const LOSS_COLOR = '#ef4444';
const ZERO_LINE_COLOR = '#ffffff';
const MEAN_LINE_COLOR = '#3b82f6';

interface RMultipleHistogramProps {
  period: PerformancePeriod;
  /** Fill available height (for matching heights in grid rows) */
  fullHeight?: boolean;
}

export function RMultipleHistogram({ period, fullHeight = false }: RMultipleHistogramProps) {
  const [strategyFilter, setStrategyFilter] = useState<string>('all');

  const strategyId = strategyFilter === 'all' ? undefined : strategyFilter;
  const { data, isLoading, error } = useDistribution(period, strategyId);

  // Transform bin data for Recharts
  const chartData = useMemo(() => {
    if (!data?.bins) return [];

    return data.bins.map((bin) => {
      // Use midpoint of bin for display
      const midpoint = (bin.range_min + bin.range_max) / 2;
      // Format label: "-1.0R" or "+0.5R"
      const label = midpoint >= 0 ? `+${midpoint.toFixed(1)}R` : `${midpoint.toFixed(1)}R`;

      return {
        label,
        midpoint,
        count: bin.count,
        range_min: bin.range_min,
        range_max: bin.range_max,
        avg_pnl: bin.avg_pnl,
        isPositive: midpoint >= 0,
      };
    });
  }, [data?.bins]);

  // Calculate skew (simplified: positive if mean > median, negative otherwise)
  const skew = useMemo(() => {
    if (!data) return null;
    const diff = data.mean_r - data.median_r;
    // Normalize to a rough skew indicator
    if (Math.abs(diff) < 0.1) return 0;
    return diff > 0 ? 1 : -1;
  }, [data]);

  if (isLoading) {
    return (
      <Card fullHeight={fullHeight}>
        <div className="px-4 pt-4 pb-2">
          <h3 className="text-sm font-medium text-argus-text">R-Multiple Distribution</h3>
        </div>
        <div className="flex-grow flex items-center justify-center min-h-[280px]">
          <div className="text-argus-text-dim">Loading distribution data...</div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card fullHeight={fullHeight}>
        <div className="px-4 pt-4 pb-2">
          <h3 className="text-sm font-medium text-argus-text">R-Multiple Distribution</h3>
        </div>
        <div className="flex-grow flex items-center justify-center min-h-[280px]">
          <div className="text-argus-loss">Failed to load distribution data</div>
        </div>
      </Card>
    );
  }

  const isEmpty = !data?.bins || data.bins.length === 0 || data.total_trades === 0;

  return (
    <Card noPadding fullHeight={fullHeight}>
      {/* Header with title and strategy filter */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 px-4 pt-4 pb-2">
        <h3 className="text-sm font-medium text-argus-text">R-Multiple Distribution</h3>
        <select
          value={strategyFilter}
          onChange={(e) => setStrategyFilter(e.target.value)}
          className="px-3 py-1.5 text-sm bg-argus-surface-2 border border-argus-border rounded-md text-argus-text focus:outline-none focus:ring-1 focus:ring-argus-accent"
          aria-label="Filter by strategy"
        >
          {STRATEGY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Chart area */}
      <div className="px-4 pb-2 flex-grow flex flex-col justify-center">
        {isEmpty ? (
          <div className="min-h-[240px] flex items-center justify-center">
            <p className="text-argus-text-dim">No trades to analyze</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart
              data={chartData}
              margin={{ top: 20, right: 20, left: 0, bottom: 5 }}
            >
              <XAxis
                dataKey="label"
                tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 10 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
                tickLine={{ stroke: 'rgba(255,255,255,0.2)' }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
                tickLine={{ stroke: 'rgba(255,255,255,0.2)' }}
                allowDecimals={false}
              />
              <Tooltip content={<CustomTooltip totalTrades={data?.total_trades ?? 0} />} />

              {/* Reference line at 0R */}
              <ReferenceLine
                x="+0.0R"
                stroke={ZERO_LINE_COLOR}
                strokeDasharray="4 4"
                strokeOpacity={0.6}
              />

              {/* Reference line at mean R */}
              {data && data.mean_r !== 0 && (
                <ReferenceLine
                  x={data.mean_r >= 0 ? `+${data.mean_r.toFixed(1)}R` : `${data.mean_r.toFixed(1)}R`}
                  stroke={MEAN_LINE_COLOR}
                  strokeDasharray="4 4"
                  strokeWidth={2}
                  label={{
                    value: 'Mean',
                    position: 'top',
                    fill: MEAN_LINE_COLOR,
                    fontSize: 10,
                  }}
                />
              )}

              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.isPositive ? PROFIT_COLOR : LOSS_COLOR}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Annotation row */}
      {!isEmpty && data && (
        <div className="px-4 pb-4 text-center">
          <span className="text-xs text-argus-text-dim">
            Mean:{' '}
            <span className={data.mean_r >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
              {data.mean_r >= 0 ? '+' : ''}{data.mean_r.toFixed(2)}R
            </span>
            {' | '}
            Median:{' '}
            <span className={data.median_r >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
              {data.median_r >= 0 ? '+' : ''}{data.median_r.toFixed(2)}R
            </span>
            {skew !== null && (
              <>
                {' | '}
                Skew:{' '}
                <span className="text-argus-text">
                  {skew > 0 ? '+' : skew < 0 ? '-' : ''}
                  {Math.abs(skew) < 0.5 ? '0' : skew > 0 ? '+' : '-'}
                </span>
              </>
            )}
          </span>
        </div>
      )}
    </Card>
  );
}

// Custom tooltip component
interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: {
      label: string;
      range_min: number;
      range_max: number;
      count: number;
      avg_pnl: number;
      isPositive: boolean;
    };
  }>;
  totalTrades: number;
}

function CustomTooltip({ active, payload, totalTrades }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const data = payload[0].payload;
  const pctOfTotal = totalTrades > 0 ? ((data.count / totalTrades) * 100).toFixed(1) : '0';

  return (
    <div className="px-3 py-2 rounded-lg bg-argus-surface-2 border border-argus-border shadow-lg">
      <div className="text-xs space-y-1">
        <div className="text-argus-text font-medium">
          {data.range_min.toFixed(2)}R to {data.range_max.toFixed(2)}R
        </div>
        <div className="text-argus-text-dim">
          Count: <span className="text-argus-text">{data.count}</span>
        </div>
        <div className="text-argus-text-dim">
          % of Total: <span className="text-argus-text">{pctOfTotal}%</span>
        </div>
        <div className="text-argus-text-dim">
          Avg P&L:{' '}
          <span className={data.avg_pnl >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
            {data.avg_pnl >= 0 ? '+' : ''}${data.avg_pnl.toFixed(0)}
          </span>
        </div>
      </div>
    </div>
  );
}
