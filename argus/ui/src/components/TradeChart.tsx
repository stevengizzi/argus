/**
 * Trade analysis chart with price level overlays.
 *
 * Displays candlestick data for a trade's time window with entry/exit markers
 * and price level overlays (stop, targets). Used in both TradeDetailPanel
 * (closed trades) and PositionDetailPanel (open positions).
 *
 * Uses TradingView Lightweight Charts v5 API for high-performance charting.
 */

import { useRef, useEffect, useMemo } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type CandlestickData,
  type UTCTimestamp,
  type Time,
  type SeriesMarker,
  LineStyle,
} from 'lightweight-charts';
import { useTradeChartBars } from '../hooks/useSymbolBars';
import { chartColors, lwcDefaultOptions } from '../utils/chartTheme';

export interface TradeChartProps {
  symbol: string;
  entryTime: string;
  exitTime?: string;
  entryPrice: number;
  exitPrice?: number;
  stopPrice?: number;
  targetPrices?: number[];
  currentPrice?: number;
  isOpen?: boolean;
}

/**
 * Validate that a value is a finite number suitable for chart display.
 */
function isValidPrice(value: unknown): value is number {
  return typeof value === 'number' && isFinite(value) && value > 0;
}

/**
 * Compute time range for bar fetching.
 * Scales padding with hold duration: max(50% of hold duration, 5 minutes).
 * This ensures short trades fill ~33% of chart width, longer trades ~50%.
 * Returns null if dates are invalid.
 */
function computeTimeRange(
  entryTime: string,
  exitTime: string | undefined,
  isOpen: boolean,
): { startTime: string; endTime: string } | null {
  const entryDate = new Date(entryTime);

  // Validate entry date
  if (isNaN(entryDate.getTime())) {
    return null;
  }

  let endDate: Date;
  if (isOpen || !exitTime) {
    // For open positions, use current time + 1 minute buffer
    endDate = new Date(Date.now() + 60 * 1000);
  } else {
    const exitDate = new Date(exitTime);
    if (isNaN(exitDate.getTime())) {
      // Invalid exit time, use current time as fallback
      endDate = new Date(Date.now() + 60 * 1000);
    } else {
      endDate = exitDate;
    }
  }

  // Scale padding with hold duration: max(50% of hold, 5 minutes)
  const holdMs = endDate.getTime() - entryDate.getTime();
  const minPaddingMs = 5 * 60 * 1000; // 5 minutes
  const paddingMs = Math.max(holdMs * 0.5, minPaddingMs);

  const startDate = new Date(entryDate.getTime() - paddingMs);
  const endDateWithPadding = new Date(endDate.getTime() + paddingMs);

  return {
    startTime: startDate.toISOString(),
    endTime: endDateWithPadding.toISOString(),
  };
}

export function TradeChart({
  symbol,
  entryTime,
  exitTime,
  entryPrice,
  exitPrice,
  stopPrice,
  targetPrices,
  currentPrice,
  isOpen = false,
}: TradeChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);

  // Compute time range for data fetching (null if dates are invalid)
  const timeRange = useMemo(
    () => computeTimeRange(entryTime, exitTime, isOpen),
    [entryTime, exitTime, isOpen]
  );

  const { data: barsData, isLoading, error } = useTradeChartBars(
    symbol,
    timeRange?.startTime ?? null,
    timeRange?.endTime ?? null
  );

  // Transform bars data to Lightweight Charts format
  const chartData = useMemo(() => {
    if (!barsData?.bars?.length) return { candles: [], entryBarIndex: -1, exitBarIndex: -1 };

    const candles: CandlestickData<UTCTimestamp>[] = [];
    let entryBarIndex = -1;
    let exitBarIndex = -1;
    const entryTimestamp = new Date(entryTime).getTime();
    const exitTimestamp = exitTime ? new Date(exitTime).getTime() : null;

    for (let i = 0; i < barsData.bars.length; i++) {
      const bar = barsData.bars[i];
      const barTimestamp = new Date(bar.timestamp).getTime();
      const time = Math.floor(barTimestamp / 1000) as UTCTimestamp;

      candles.push({
        time,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      });

      // Find entry bar (first bar at or after entry time)
      if (entryBarIndex === -1 && barTimestamp >= entryTimestamp) {
        entryBarIndex = i;
      }

      // Find exit bar (first bar at or after exit time)
      if (exitTimestamp && exitBarIndex === -1 && barTimestamp >= exitTimestamp) {
        exitBarIndex = i;
      }
    }

    return { candles, entryBarIndex, exitBarIndex };
  }, [barsData, entryTime, exitTime]);

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

    // Add candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: chartColors.profit,
      downColor: chartColors.loss,
      borderVisible: false,
      wickUpColor: chartColors.profit,
      wickDownColor: chartColors.loss,
    });
    candleSeriesRef.current = candleSeries;

    // Create markers plugin for entry/exit markers
    const markersPlugin = createSeriesMarkers(candleSeries, []);
    markersPluginRef.current = markersPlugin;

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
      markersPluginRef.current = null;
    };
  }, []);

  // Update data and overlays when bars change
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const chart = chartRef.current;
    if (!candleSeries || !chart || chartData.candles.length === 0) return;

    // Set candlestick data
    candleSeries.setData(chartData.candles);

    // Remove all previously created price lines before recreating
    priceLinesRef.current.forEach(line => candleSeries.removePriceLine(line));
    priceLinesRef.current = [];

    // Add price level overlays
    // Entry price: Blue dashed line (only if valid)
    if (isValidPrice(entryPrice)) {
      const entryLine = candleSeries.createPriceLine({
        price: entryPrice,
        color: '#3b82f6', // Blue
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: `Entry`,
      });
      priceLinesRef.current.push(entryLine);
    }

    // Stop price: Red solid line
    if (isValidPrice(stopPrice)) {
      const stopLine = candleSeries.createPriceLine({
        price: stopPrice,
        color: '#ef4444', // Red
        lineWidth: 1,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        title: 'Stop',
      });
      priceLinesRef.current.push(stopLine);
    }

    // T1 price: Green dashed line
    if (isValidPrice(targetPrices?.[0])) {
      const t1Line = candleSeries.createPriceLine({
        price: targetPrices![0],
        color: '#22c55e', // Green
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: 'T1',
      });
      priceLinesRef.current.push(t1Line);
    }

    // T2 price: Green dotted line
    if (isValidPrice(targetPrices?.[1])) {
      const t2Line = candleSeries.createPriceLine({
        price: targetPrices![1],
        color: '#22c55e', // Green
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: true,
        title: 'T2',
      });
      priceLinesRef.current.push(t2Line);
    }

    // Exit price: Orange solid line (closed trades only, if differs from entry by > $0.01)
    if (!isOpen && isValidPrice(exitPrice) && isValidPrice(entryPrice) && Math.abs(exitPrice - entryPrice) > 0.01) {
      const exitLine = candleSeries.createPriceLine({
        price: exitPrice,
        color: '#f97316', // Orange
        lineWidth: 1,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        title: 'Exit',
      });
      priceLinesRef.current.push(exitLine);
    }

    // Current price: Cyan dashed line (open positions only)
    if (isOpen && isValidPrice(currentPrice)) {
      const currentLine = candleSeries.createPriceLine({
        price: currentPrice,
        color: '#06b6d4', // Cyan
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: 'Current',
      });
      priceLinesRef.current.push(currentLine);
    }

    // Add markers for entry/exit via plugin
    const markers: SeriesMarker<Time>[] = [];

    // Entry marker - blue up-arrow for visibility on all candle colors
    if (chartData.entryBarIndex >= 0 && chartData.candles[chartData.entryBarIndex]) {
      markers.push({
        time: chartData.candles[chartData.entryBarIndex].time,
        position: 'belowBar',
        color: '#60a5fa', // Blue - visible against both green and red candles
        shape: 'arrowUp',
        text: 'Entry',
      });
    }

    // Exit marker (for closed trades) - blue down-arrow for visibility on all candle colors
    if (!isOpen && chartData.exitBarIndex >= 0 && chartData.candles[chartData.exitBarIndex]) {
      markers.push({
        time: chartData.candles[chartData.exitBarIndex].time,
        position: 'aboveBar',
        color: '#60a5fa', // Blue - visible against both green and red candles
        shape: 'arrowDown',
        text: 'Exit',
      });
    }

    if (markersPluginRef.current) {
      markersPluginRef.current.setMarkers(markers);
    }

    // Fit content after data update
    chart.timeScale().fitContent();

    return () => {
      const series = candleSeriesRef.current;
      if (series) {
        priceLinesRef.current.forEach(line => series.removePriceLine(line));
        priceLinesRef.current = [];
      }
    };
  }, [chartData, entryPrice, exitPrice, stopPrice, targetPrices, currentPrice, isOpen]);

  const hasNoBars = !isLoading && !error && (!barsData?.bars?.length);
  const hasInvalidTimeRange = timeRange === null;

  return (
    <div className="bg-argus-surface-2 rounded-lg border border-argus-border overflow-hidden relative">
      {/* Chart container - always mounted so ref is available */}
      <div
        ref={containerRef}
        className={`h-[250px] ${isLoading || error || hasNoBars || hasInvalidTimeRange ? 'invisible' : ''}`}
        data-testid="trade-chart-container"
      />

      {/* Loading overlay */}
      {isLoading && !hasInvalidTimeRange && (
        <div className="absolute inset-0 h-[250px] flex items-center justify-center bg-argus-surface-2">
          <Loader2 className="w-8 h-8 text-argus-text-dim animate-spin" />
        </div>
      )}

      {/* Empty state */}
      {hasNoBars && !hasInvalidTimeRange && (
        <div className="absolute inset-0 h-[250px] flex flex-col items-center justify-center gap-2 text-argus-text-dim bg-argus-surface-2">
          <AlertCircle className="w-6 h-6" />
          <span className="text-sm">Bar data not available for this trade</span>
        </div>
      )}

      {/* Invalid time range or error overlay */}
      {(error || hasInvalidTimeRange) && !isLoading && (
        <div className="absolute inset-0 h-[250px] flex flex-col items-center justify-center gap-2 text-argus-text-dim bg-argus-surface-2">
          <AlertCircle className="w-6 h-6 text-argus-loss" />
          <span className="text-sm">Chart unavailable</span>
        </div>
      )}
    </div>
  );
}
