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
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type UTCTimestamp,
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
 * Compute time range for bar fetching.
 * Adds 15 minutes padding before entry and after exit.
 */
function computeTimeRange(
  entryTime: string,
  exitTime: string | undefined,
  isOpen: boolean,
): { startTime: string; endTime: string } {
  const entryDate = new Date(entryTime);
  const startDate = new Date(entryDate.getTime() - 15 * 60 * 1000);

  let endDate: Date;
  if (isOpen || !exitTime) {
    // For open positions, use current time + 1 minute buffer
    endDate = new Date(Date.now() + 60 * 1000);
  } else {
    endDate = new Date(new Date(exitTime).getTime() + 15 * 60 * 1000);
  }

  return {
    startTime: startDate.toISOString(),
    endTime: endDate.toISOString(),
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

  // Compute time range for data fetching
  const { startTime, endTime } = useMemo(
    () => computeTimeRange(entryTime, exitTime, isOpen),
    [entryTime, exitTime, isOpen]
  );

  const { data: barsData, isLoading, error } = useTradeChartBars(symbol, startTime, endTime);

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
    };
  }, []);

  // Update data and overlays when bars change
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const chart = chartRef.current;
    if (!candleSeries || !chart || chartData.candles.length === 0) return;

    // Set candlestick data
    candleSeries.setData(chartData.candles);

    // Clear existing price lines
    // Note: We recreate them each time data changes

    // Add price level overlays
    // Entry price: Blue dashed line
    candleSeries.createPriceLine({
      price: entryPrice,
      color: '#3b82f6', // Blue
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: `Entry`,
    });

    // Stop price: Red solid line
    if (stopPrice && stopPrice > 0) {
      candleSeries.createPriceLine({
        price: stopPrice,
        color: '#ef4444', // Red
        lineWidth: 1,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        title: 'Stop',
      });
    }

    // T1 price: Green dashed line
    if (targetPrices?.[0] && targetPrices[0] > 0) {
      candleSeries.createPriceLine({
        price: targetPrices[0],
        color: '#22c55e', // Green
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: 'T1',
      });
    }

    // T2 price: Green dotted line (only if > 0)
    if (targetPrices?.[1] && targetPrices[1] > 0) {
      candleSeries.createPriceLine({
        price: targetPrices[1],
        color: '#22c55e', // Green
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: true,
        title: 'T2',
      });
    }

    // Exit price: Orange solid line (closed trades only, if differs from entry by > $0.01)
    if (!isOpen && exitPrice && Math.abs(exitPrice - entryPrice) > 0.01) {
      candleSeries.createPriceLine({
        price: exitPrice,
        color: '#f97316', // Orange
        lineWidth: 1,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        title: 'Exit',
      });
    }

    // Current price: Cyan dashed line (open positions only)
    if (isOpen && currentPrice && currentPrice > 0) {
      candleSeries.createPriceLine({
        price: currentPrice,
        color: '#06b6d4', // Cyan
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: 'Current',
      });
    }

    // Add markers for entry/exit
    const markers: SeriesMarker<UTCTimestamp>[] = [];

    // Entry marker
    if (chartData.entryBarIndex >= 0 && chartData.candles[chartData.entryBarIndex]) {
      markers.push({
        time: chartData.candles[chartData.entryBarIndex].time,
        position: 'belowBar',
        color: '#3b82f6', // Blue
        shape: 'arrowUp',
        text: 'Entry',
      });
    }

    // Exit marker (for closed trades)
    if (!isOpen && chartData.exitBarIndex >= 0 && chartData.candles[chartData.exitBarIndex]) {
      const isWin = exitPrice && exitPrice > entryPrice;
      markers.push({
        time: chartData.candles[chartData.exitBarIndex].time,
        position: 'aboveBar',
        color: isWin ? '#22c55e' : '#ef4444',
        shape: isWin ? 'arrowUp' : 'arrowDown',
        text: 'Exit',
      });
    }

    candleSeries.setMarkers(markers);

    // Fit content after data update
    chart.timeScale().fitContent();
  }, [chartData, entryPrice, exitPrice, stopPrice, targetPrices, currentPrice, isOpen]);

  const hasNoBars = !isLoading && !error && (!barsData?.bars?.length);

  return (
    <div className="bg-argus-surface-2 rounded-lg border border-argus-border overflow-hidden relative">
      {/* Chart container - always mounted so ref is available */}
      <div
        ref={containerRef}
        className={`h-[250px] ${isLoading || error || hasNoBars ? 'invisible' : ''}`}
        data-testid="trade-chart-container"
      />

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 h-[250px] flex items-center justify-center bg-argus-surface-2">
          <Loader2 className="w-8 h-8 text-argus-text-dim animate-spin" />
        </div>
      )}

      {/* Empty state */}
      {hasNoBars && (
        <div className="absolute inset-0 h-[250px] flex flex-col items-center justify-center gap-2 text-argus-text-dim bg-argus-surface-2">
          <AlertCircle className="w-6 h-6" />
          <span className="text-sm">Bar data not available for this trade</span>
        </div>
      )}

      {/* Error overlay */}
      {error && !isLoading && (
        <div className="absolute inset-0 h-[250px] flex flex-col items-center justify-center gap-2 text-argus-text-dim bg-argus-surface-2">
          <AlertCircle className="w-6 h-6 text-argus-loss" />
          <span className="text-sm">Chart unavailable</span>
        </div>
      )}
    </div>
  );
}
