/**
 * Daily P&L histogram using TradingView Lightweight Charts HistogramSeries.
 *
 * Green bars for positive days, red for negative.
 * Heights: 250px desktop, 200px tablet, 160px mobile.
 * Card container is stable; only chart content dims during period transitions.
 */

import { useCallback, useEffect, useRef, useMemo } from 'react';
import { HistogramSeries, type IChartApi, type ISeriesApi, type HistogramData, type Time } from 'lightweight-charts';
import { LWChart } from '../../components/LWChart';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { chartColors } from '../../utils/chartTheme';
import { animateChartDrawIn } from '../../utils/chartAnimation';
import type { DailyPnlEntry } from '../../api/types';

interface DailyPnlChartProps {
  dailyPnl: DailyPnlEntry[];
  isTransitioning?: boolean;
  className?: string;
}

function useResponsiveHeight(): number {
  if (typeof window === 'undefined') return 250;
  if (window.innerWidth < 640) return 160;
  if (window.innerWidth < 1024) return 200;
  return 250;
}

export function DailyPnlChart({ dailyPnl, isTransitioning = false, className = '' }: DailyPnlChartProps) {
  const chartHeight = useResponsiveHeight();
  const seriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  // Memoize histogram data - sort ascending by date (Lightweight Charts requirement)
  const histogramData: HistogramData<Time>[] = useMemo(() => {
    const sorted = [...dailyPnl].sort((a, b) => a.date.localeCompare(b.date));
    return sorted.map((entry) => ({
      time: entry.date as Time,
      value: entry.pnl,
      color: entry.pnl >= 0 ? chartColors.profit : chartColors.loss,
    }));
  }, [dailyPnl]);

  // Store latest data in ref for use in callback
  const dataRef = useRef(histogramData);

  // Update ref when data changes (must be in effect, not during render)
  useEffect(() => {
    dataRef.current = histogramData;
  }, [histogramData]);

  const handleChartReady = useCallback((chart: IChartApi) => {
    chartRef.current = chart;

    // Add histogram series (v5 API)
    const series = chart.addSeries(HistogramSeries, {
      lastValueVisible: false, // No last value label for histogram
      priceLineVisible: false, // No price line for histogram
      priceFormat: {
        type: 'custom',
        formatter: (price: number) => {
          const sign = price >= 0 ? '+' : '';
          return `${sign}$${price.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
        },
      },
    });

    seriesRef.current = series;

    // Animate initial data draw-in (left-to-right reveal)
    if (dataRef.current.length > 0) {
      animateChartDrawIn(series, dataRef.current, chart);
    }
  }, []);

  // Update data when it changes
  useEffect(() => {
    if (seriesRef.current && chartRef.current && histogramData.length > 0) {
      seriesRef.current.setData(histogramData);
      chartRef.current.timeScale().fitContent();
    }
  }, [histogramData]);

  // The card container always renders (never conditionally unmounted)
  return (
    <Card className={className} noPadding>
      <div className="p-4 pb-0">
        <CardHeader title="Daily P&L" />
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
