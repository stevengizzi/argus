/**
 * Live-updating candlestick chart for the Observatory detail panel.
 *
 * Wraps Lightweight Charts createChart() with a candlestick series.
 * Reinitializes chart on symbol change, disposes on unmount.
 * Data sourced from fetchSymbolBars via the parent's useSymbolDetail hook.
 *
 * Sprint 25, Session 4b.
 */

import { useRef, useEffect, useMemo } from 'react';
import {
  createChart,
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type UTCTimestamp,
} from 'lightweight-charts';
import { chartColors, lwcDefaultOptions } from '../../../utils/chartTheme';
import type { BarData } from '../../../api/types';

interface SymbolCandlestickChartProps {
  symbol: string;
  bars: BarData[];
  height?: number;
}

export function SymbolCandlestickChart({
  symbol,
  bars,
  height = 200,
}: SymbolCandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  const chartData = useMemo(() => {
    if (!bars.length) return [];

    return bars.map((bar): CandlestickData<UTCTimestamp> => ({
      time: Math.floor(new Date(bar.timestamp).getTime() / 1000) as UTCTimestamp,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }));
  }, [bars]);

  // Create/destroy chart when symbol changes (full reinit, not just data swap)
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      ...lwcDefaultOptions,
      layout: {
        ...lwcDefaultOptions.layout,
        background: { color: 'transparent' },
        fontSize: 10,
      },
      width: container.clientWidth,
      height,
      timeScale: {
        ...lwcDefaultOptions.timeScale,
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        ...lwcDefaultOptions.rightPriceScale,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: chartColors.border, style: 3 },
      },
    });

    chartRef.current = chart;

    const series = chart.addSeries(CandlestickSeries, {
      upColor: chartColors.profit,
      downColor: chartColors.loss,
      borderVisible: false,
      wickUpColor: chartColors.profit,
      wickDownColor: chartColors.loss,
    });
    seriesRef.current = series;

    const resizeObserver = new ResizeObserver(() => {
      if (chartRef.current && container) {
        chartRef.current.applyOptions({ width: container.clientWidth });
      }
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [symbol, height]);

  // Update data when bars change
  useEffect(() => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || !chart || chartData.length === 0) return;

    series.setData(chartData);
    chart.timeScale().fitContent();
  }, [chartData]);

  return (
    <div
      ref={containerRef}
      className="overflow-hidden rounded"
      style={{ height: `${height}px` }}
      data-testid="symbol-candlestick-chart"
    />
  );
}
