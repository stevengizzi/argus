/**
 * MiniChart: TradingView Lightweight Charts candlestick chart for Arena cards.
 *
 * Pure component — no data fetching, no WebSocket. Accepts candles and price
 * level props, renders a compact dark-themed chart, and exposes an imperative
 * handle for live tick updates in S11.
 */

import { useRef, useEffect, useImperativeHandle, forwardRef } from 'react';
import {
  createChart,
  CandlestickSeries,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type UTCTimestamp,
} from 'lightweight-charts';
import { chartColors, lwcDefaultOptions } from '../../utils/chartTheme';

/** Candle shape accepted by MiniChart and ArenaCard. */
export interface CandleData {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
}

/** Imperative handle exposed via forwardRef for S11 live updates. */
export interface MiniChartHandle {
  updateCandle: (candle: CandleData) => void;
  appendCandle: (candle: CandleData) => void;
  updateTrailingStop: (price: number) => void;
}

export interface MiniChartProps {
  candles: CandleData[];
  entryPrice?: number;
  stopPrice?: number;
  targetPrices?: number[];
  trailingStopPrice?: number;
  width?: number;
  height?: number;
}

type PriceLine = ReturnType<ISeriesApi<'Candlestick'>['createPriceLine']>;

function isValidPrice(value: unknown): value is number {
  return typeof value === 'number' && isFinite(value) && value > 0;
}

export const MiniChart = forwardRef<MiniChartHandle, MiniChartProps>(
  function MiniChart(
    { candles, entryPrice, stopPrice, targetPrices, trailingStopPrice, width, height = 160 },
    ref,
  ) {
    const containerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
    const priceLinesRef = useRef<PriceLine[]>([]);
    const trailingStopLineRef = useRef<PriceLine | null>(null);

    // Chart creation and cleanup — re-runs only when dimensions change.
    useEffect(() => {
      const container = containerRef.current;
      if (!container) return;

      const chart = createChart(container, {
        ...lwcDefaultOptions,
        width: width ?? container.clientWidth,
        height,
        layout: {
          ...lwcDefaultOptions.layout,
          background: { color: 'transparent' },
        },
        grid: {
          vertLines: { color: '#1e2130' },
          horzLines: { color: '#1e2130' },
        },
        timeScale: {
          borderColor: chartColors.border,
          timeVisible: true,
          secondsVisible: false,
        },
        rightPriceScale: {
          borderColor: chartColors.border,
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
        if (chartRef.current && container && !width) {
          chartRef.current.applyOptions({ width: container.clientWidth });
        }
      });
      resizeObserver.observe(container);

      return () => {
        resizeObserver.disconnect();
        priceLinesRef.current = [];
        trailingStopLineRef.current = null;
        chart.remove();
        chartRef.current = null;
        seriesRef.current = null;
      };
    }, [width, height]);

    // Update candle data and price lines when props change (S4 cleanup pattern).
    useEffect(() => {
      const series = seriesRef.current;
      const chart = chartRef.current;
      if (!series || !chart) return;

      if (candles.length > 0) {
        series.setData(candles as CandlestickData<UTCTimestamp>[]);
        chart.timeScale().fitContent();
      }

      // Remove existing static price lines before recreating them.
      priceLinesRef.current.forEach((line) => {
        try {
          series.removePriceLine(line);
        } catch {
          // Line may already be gone if chart was recreated.
        }
      });
      priceLinesRef.current = [];

      if (isValidPrice(entryPrice)) {
        priceLinesRef.current.push(
          series.createPriceLine({
            price: entryPrice,
            color: '#3b82f6',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'Entry',
          }),
        );
      }

      if (isValidPrice(stopPrice)) {
        priceLinesRef.current.push(
          series.createPriceLine({
            price: stopPrice,
            color: '#ef4444',
            lineWidth: 1,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            title: 'Stop',
          }),
        );
      }

      if (isValidPrice(targetPrices?.[0])) {
        priceLinesRef.current.push(
          series.createPriceLine({
            price: targetPrices![0],
            color: '#22c55e',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'T1',
          }),
        );
      }

      // Trailing stop uses a separate ref so it can be updated in isolation.
      if (trailingStopLineRef.current) {
        try {
          series.removePriceLine(trailingStopLineRef.current);
        } catch {
          // Already removed.
        }
        trailingStopLineRef.current = null;
      }

      if (isValidPrice(trailingStopPrice)) {
        trailingStopLineRef.current = series.createPriceLine({
          price: trailingStopPrice,
          color: '#eab308',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: 'Trail',
        });
      }
    }, [candles, entryPrice, stopPrice, targetPrices, trailingStopPrice]);

    // Imperative handle for live updates from S11 WebSocket feed.
    useImperativeHandle(ref, () => ({
      updateCandle: (candle: CandleData) => {
        seriesRef.current?.update(candle as CandlestickData<UTCTimestamp>);
      },
      appendCandle: (candle: CandleData) => {
        seriesRef.current?.update(candle as CandlestickData<UTCTimestamp>);
      },
      updateTrailingStop: (price: number) => {
        const series = seriesRef.current;
        if (!series) return;
        if (trailingStopLineRef.current) {
          trailingStopLineRef.current.applyOptions({ price });
        } else {
          trailingStopLineRef.current = series.createPriceLine({
            price,
            color: '#eab308',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'Trail',
          });
        }
      },
    }));

    return (
      <div
        ref={containerRef}
        style={{ width: width ? `${width}px` : '100%', height: `${height}px` }}
        data-testid="mini-chart-container"
      />
    );
  },
);
