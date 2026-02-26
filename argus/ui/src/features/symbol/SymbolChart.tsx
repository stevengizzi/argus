/**
 * Symbol candlestick chart with volume histogram.
 *
 * Session 7: Placeholder component showing symbol header and chart stub.
 * Session 8: Full LWChart candlestick + volume implementation.
 *
 * Uses TradingView Lightweight Charts v5 API for high-performance charting.
 */

import { useRef, useEffect, useMemo } from 'react';
import { AlertCircle } from 'lucide-react';
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type HistogramData,
  type UTCTimestamp,
} from 'lightweight-charts';
import { useSymbolBars } from '../../hooks/useSymbolBars';
import { usePositions } from '../../hooks/usePositions';
import { formatPrice } from '../../utils/format';
import { chartColors, lwcDefaultOptions } from '../../utils/chartTheme';

interface SymbolChartProps {
  symbol: string;
}

export function SymbolChart({ symbol }: SymbolChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  const { data: barsData, isLoading, error } = useSymbolBars(symbol);
  const { data: positionsData } = usePositions();

  // Try to get current price from positions data or bars
  const position = positionsData?.positions.find((p) => p.symbol === symbol);
  const lastBar = barsData?.bars[barsData.bars.length - 1];
  const currentPrice = position?.current_price ?? lastBar?.close;

  // Transform bars data to Lightweight Charts format
  const chartData = useMemo(() => {
    if (!barsData?.bars?.length) return { candles: [], volume: [] };

    const candles: CandlestickData<UTCTimestamp>[] = [];
    const volume: HistogramData<UTCTimestamp>[] = [];

    for (const bar of barsData.bars) {
      const time = Math.floor(new Date(bar.timestamp).getTime() / 1000) as UTCTimestamp;
      const isUp = bar.close >= bar.open;

      candles.push({
        time,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      });

      volume.push({
        time,
        value: bar.volume,
        color: isUp ? chartColors.profit + '60' : chartColors.loss + '60', // 60 = ~38% opacity
      });
    }

    return { candles, volume };
  }, [barsData]);

  // Create/destroy chart on mount/unmount
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Create chart with merged options
    const chart = createChart(container, {
      ...lwcDefaultOptions,
      width: container.clientWidth,
      height: 250,
      timeScale: {
        ...lwcDefaultOptions.timeScale,
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add candlestick series (main pane)
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: chartColors.profit,
      downColor: chartColors.loss,
      borderVisible: false,
      wickUpColor: chartColors.profit,
      wickDownColor: chartColors.loss,
    });
    candleSeriesRef.current = candleSeries;

    // Add volume histogram series (separate pane below candles)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
    });

    // Configure volume pane to be smaller
    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.85, // Volume pane at bottom 15%
        bottom: 0,
      },
    });

    volumeSeriesRef.current = volumeSeries;

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
      if (chartRef.current && container) {
        chartRef.current.applyOptions({
          width: container.clientWidth,
        });
      }
    });
    resizeObserver.observe(container);

    // Cleanup
    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, []);

  // Update data when bars change
  useEffect(() => {
    if (candleSeriesRef.current && chartData.candles.length > 0) {
      candleSeriesRef.current.setData(chartData.candles);
    }
    if (volumeSeriesRef.current && chartData.volume.length > 0) {
      volumeSeriesRef.current.setData(chartData.volume);
    }
    // Fit content after data update
    if (chartRef.current && chartData.candles.length > 0) {
      chartRef.current.timeScale().fitContent();
    }
  }, [chartData]);

  return (
    <div className="space-y-3">
      {/* Header with symbol and price */}
      <div className="flex items-baseline justify-between">
        <h2 className="text-2xl font-bold text-argus-text">{symbol}</h2>
        {currentPrice != null ? (
          <span className="text-xl font-medium tabular-nums text-argus-text">
            {formatPrice(currentPrice)}
          </span>
        ) : (
          <span className="text-sm text-argus-text-dim">Price data loading...</span>
        )}
      </div>

      {/* Chart container - always render to avoid ref timing issues */}
      <div className="bg-argus-surface-2 rounded-lg border border-argus-border overflow-hidden relative">
        {/* Chart container - always mounted so ref is available */}
        <div
          ref={containerRef}
          className={`h-[250px] md:h-[300px] ${isLoading || error ? 'invisible' : ''}`}
        />

        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 h-[250px] md:h-[300px] animate-pulse bg-argus-surface-3" />
        )}

        {/* Error overlay */}
        {error && !isLoading && (
          <div className="absolute inset-0 h-[250px] md:h-[300px] flex flex-col items-center justify-center gap-2 text-argus-text-dim bg-argus-surface-2">
            <AlertCircle className="w-8 h-8 text-argus-loss" />
            <span className="text-sm">Unable to load chart data</span>
          </div>
        )}
      </div>
    </div>
  );
}
