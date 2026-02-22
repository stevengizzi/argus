/**
 * Equity curve chart using TradingView Lightweight Charts AreaSeries.
 *
 * Shows cumulative P&L over time with gradient fill.
 * Heights: 300px desktop, 220px tablet, 180px mobile.
 */

import { useCallback, useEffect, useRef, useMemo } from 'react';
import { AreaSeries, type IChartApi, type ISeriesApi, type AreaData, type Time } from 'lightweight-charts';
import { LWChart } from '../../components/LWChart';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { chartColors } from '../../utils/chartTheme';
import type { DailyPnlEntry } from '../../api/types';

interface EquityCurveProps {
  dailyPnl: DailyPnlEntry[];
  className?: string;
}

function useResponsiveHeight(): number {
  if (typeof window === 'undefined') return 300;
  if (window.innerWidth < 640) return 180;
  if (window.innerWidth < 1024) return 220;
  return 300;
}

export function EquityCurve({ dailyPnl, className = '' }: EquityCurveProps) {
  const chartHeight = useResponsiveHeight();
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

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

    // Set initial data from ref
    if (dataRef.current.length > 0) {
      series.setData(dataRef.current);
      chart.timeScale().fitContent();
    }
  }, []);

  // Update data when it changes
  useEffect(() => {
    if (seriesRef.current && chartRef.current && equityData.length > 0) {
      seriesRef.current.setData(equityData);
      chartRef.current.timeScale().fitContent();
    }
  }, [equityData]);

  if (dailyPnl.length === 0) {
    return (
      <Card className={className}>
        <CardHeader title="Equity Curve" />
        <div
          className="flex items-center justify-center text-argus-text-dim text-sm"
          style={{ height: chartHeight }}
        >
          Not enough data for this period
        </div>
      </Card>
    );
  }

  return (
    <Card className={className} noPadding>
      <div className="p-4 pb-0">
        <CardHeader title="Equity Curve" />
      </div>
      <LWChart
        height={chartHeight}
        onChartReady={handleChartReady}
        className="w-full"
      />
    </Card>
  );
}
