/**
 * Equity curve chart using TradingView Lightweight Charts AreaSeries.
 *
 * Shows cumulative P&L over time with gradient fill.
 * Heights: 300px desktop, 220px tablet, 180px mobile.
 * Card container is stable; only chart content dims during period transitions.
 *
 * Sprint 21d: Added comparative period overlay (DEC-208).
 * When enabled, shows a ghost line for previous period data shifted to align
 * with current period start date.
 */

import { useCallback, useEffect, useRef, useMemo, useState } from 'react';
import {
  AreaSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type AreaData,
  type LineData,
  type Time,
} from 'lightweight-charts';
import { LWChart } from '../../components/LWChart';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { useResponsiveHeight } from '../../hooks/useMediaQuery';
import { chartColors } from '../../utils/chartTheme';
import { animateChartDrawIn } from '../../utils/chartAnimation';
import type { DailyPnlEntry, PerformancePeriod } from '../../api/types';

interface EquityCurveProps {
  dailyPnl: DailyPnlEntry[];
  isTransitioning?: boolean;
  className?: string;
  /** When true, uses reduced padding and height for constrained spaces */
  compact?: boolean;
  /** The current period for labeling comparison toggle */
  period?: PerformancePeriod;
  /** When true, shows comparison toggle and comparison series if data provided */
  showComparison?: boolean;
  /** Previous period data for comparison overlay */
  comparisonData?: DailyPnlEntry[];
  /** Callback when comparison toggle changes */
  onComparisonToggle?: (enabled: boolean) => void;
}

export function EquityCurve({
  dailyPnl,
  isTransitioning = false,
  className = '',
  compact = false,
  period = 'month',
  showComparison = false,
  comparisonData,
  onComparisonToggle,
}: EquityCurveProps) {
  // Compact mode uses smaller heights: 160px vs 300/220/180 normal
  const normalHeight = useResponsiveHeight(300, 220, 180);
  const chartHeight = compact ? 160 : normalHeight;
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const comparisonSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [comparisonEnabled, setComparisonEnabled] = useState(false);

  // Period label for comparison toggle
  const periodLabel = useMemo(() => {
    switch (period) {
      case 'week': return 'week';
      case 'month': return 'month';
      case 'all': return 'period';
      default: return 'day';
    }
  }, [period]);

  // Memoize equity data - sort ascending by date (Lightweight Charts requirement)
  const equityData: AreaData<Time>[] = useMemo(() => {
    // Sort by date ascending (oldest first)
    const sorted = [...dailyPnl].sort((a, b) => a.date.localeCompare(b.date));
    // Use reduce to compute cumulative values without reassigning a let variable
    return sorted.reduce<{ data: AreaData<Time>[]; cumulative: number }>(
      (acc, entry) => {
        const newCumulative = acc.cumulative + entry.pnl;
        acc.data.push({
          time: entry.date as Time,
          value: newCumulative,
        });
        acc.cumulative = newCumulative;
        return acc;
      },
      { data: [], cumulative: 0 }
    ).data;
  }, [dailyPnl]);

  // Memoize comparison equity data - shifted to align with current period start
  const comparisonEquityData: LineData<Time>[] = useMemo(() => {
    if (!comparisonData || comparisonData.length === 0 || equityData.length === 0) {
      return [];
    }

    // Sort comparison data by date ascending
    const sorted = [...comparisonData].sort((a, b) => a.date.localeCompare(b.date));

    // Calculate date offset: shift comparison dates to align first day with current period first day
    const currentFirstDate = equityData[0]?.time as string;
    const comparisonFirstDate = sorted[0]?.date;

    if (!currentFirstDate || !comparisonFirstDate) {
      return [];
    }

    // Calculate days offset
    const currentStart = new Date(currentFirstDate);
    const comparisonStart = new Date(comparisonFirstDate);
    const daysDiff = Math.floor((currentStart.getTime() - comparisonStart.getTime()) / (1000 * 60 * 60 * 24));

    // Compute cumulative values and shift dates
    return sorted.reduce<{ data: LineData<Time>[]; cumulative: number }>(
      (acc, entry) => {
        const newCumulative = acc.cumulative + entry.pnl;
        // Shift the date by the offset
        const originalDate = new Date(entry.date);
        originalDate.setDate(originalDate.getDate() + daysDiff);
        const shiftedDate = originalDate.toISOString().split('T')[0];

        acc.data.push({
          time: shiftedDate as Time,
          value: newCumulative,
        });
        acc.cumulative = newCumulative;
        return acc;
      },
      { data: [], cumulative: 0 }
    ).data;
  }, [comparisonData, equityData]);

  // Store latest data in ref for use in callback
  const dataRef = useRef(equityData);

  // Update ref when data changes (must be in effect, not during render)
  useEffect(() => {
    dataRef.current = equityData;
  }, [equityData]);

  const handleChartReady = useCallback((chart: IChartApi) => {
    chartRef.current = chart;

    // Add area series with gradient (v5 API)
    const series = chart.addSeries(AreaSeries, {
      lineColor: chartColors.primary,
      topColor: `${chartColors.primary}40`,
      bottomColor: `${chartColors.primary}05`,
      lineWidth: 2,
      lastValueVisible: true,
      priceLineVisible: false, // Remove redundant dashed line, value shown on axis
      priceFormat: {
        type: 'custom',
        formatter: (price: number) =>
          `$${price.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
      },
    });

    seriesRef.current = series;

    // Add comparison line series (dashed, dimmer) - initially hidden
    const comparisonSeries = chart.addSeries(LineSeries, {
      color: chartColors.text,
      lineWidth: 1,
      lineStyle: 2, // Dashed
      lastValueVisible: false,
      priceLineVisible: false,
      visible: false, // Hidden by default
      priceFormat: {
        type: 'custom',
        formatter: (price: number) =>
          `$${price.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
      },
    });

    comparisonSeriesRef.current = comparisonSeries;

    // Animate initial data draw-in (left-to-right reveal)
    if (dataRef.current.length > 0) {
      animateChartDrawIn(series, dataRef.current, chart);
    }
  }, []);

  // Update data when it changes
  useEffect(() => {
    if (seriesRef.current && chartRef.current && equityData.length > 0) {
      seriesRef.current.setData(equityData);
      chartRef.current.timeScale().fitContent();
    }
  }, [equityData]);

  // Update comparison series data and visibility
  useEffect(() => {
    if (!comparisonSeriesRef.current) return;

    const shouldShow = showComparison && comparisonEnabled && comparisonEquityData.length > 0;

    if (shouldShow) {
      comparisonSeriesRef.current.setData(comparisonEquityData);
      comparisonSeriesRef.current.applyOptions({ visible: true });
    } else {
      comparisonSeriesRef.current.applyOptions({ visible: false });
    }

    // Fit content to show both series
    if (chartRef.current && shouldShow) {
      chartRef.current.timeScale().fitContent();
    }
  }, [showComparison, comparisonEnabled, comparisonEquityData]);

  // Handle toggle change
  const handleToggleComparison = useCallback(() => {
    const newValue = !comparisonEnabled;
    setComparisonEnabled(newValue);
    onComparisonToggle?.(newValue);
  }, [comparisonEnabled, onComparisonToggle]);

  // Check if comparison is available (has data)
  const canShowComparison = showComparison && comparisonData && comparisonData.length > 0;

  // The card container always renders (never conditionally unmounted)
  return (
    <Card className={className} noPadding>
      <div className={compact ? 'p-3 pb-0' : 'p-4 pb-0'}>
        <div className="flex items-center justify-between">
          <CardHeader title="Equity Curve" />

          {/* Comparison toggle */}
          {canShowComparison && (
            <label className="flex items-center gap-2 text-xs text-argus-text-dim cursor-pointer select-none">
              <input
                type="checkbox"
                checked={comparisonEnabled}
                onChange={handleToggleComparison}
                className="w-3.5 h-3.5 rounded border-argus-border bg-argus-card
                  text-argus-accent focus:ring-1 focus:ring-argus-accent focus:ring-offset-0
                  cursor-pointer"
              />
              <span>Compare with previous {periodLabel}</span>
            </label>
          )}
        </div>

        {/* Legend when comparison is enabled */}
        {canShowComparison && comparisonEnabled && (
          <div className="flex items-center gap-4 mt-2 text-xs">
            <div className="flex items-center gap-1.5">
              <div
                className="w-4 h-0.5 rounded"
                style={{ backgroundColor: chartColors.primary }}
              />
              <span className="text-argus-text">Current {periodLabel}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div
                className="w-4 h-0.5 rounded"
                style={{
                  backgroundColor: chartColors.text,
                  backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 2px, currentColor 2px, currentColor 4px)',
                }}
              />
              <span className="text-argus-text-dim">Previous {periodLabel}</span>
            </div>
          </div>
        )}
      </div>
      <div
        className={`transition-opacity duration-200 ${isTransitioning ? 'opacity-40' : 'opacity-100'}`}
      >
        {dailyPnl.length === 0 ? (
          <div
            className="flex items-center justify-center text-argus-text-dim text-sm"
            style={{ height: chartHeight }}
          >
            Not enough data for this period
          </div>
        ) : (
          <LWChart
            height={chartHeight}
            onChartReady={handleChartReady}
            className="w-full"
          />
        )}
      </div>
    </Card>
  );
}
