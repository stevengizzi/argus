/**
 * Reusable TradingView Lightweight Charts container.
 *
 * Handles chart creation, ResizeObserver, and cleanup automatically.
 * Parent components add series via onChartReady callback.
 */

import { useRef, useEffect } from 'react';
import { createChart, type IChartApi, type DeepPartial, type ChartOptions } from 'lightweight-charts';
import { lwcDefaultOptions } from '../utils/chartTheme';

interface LWChartProps {
  /** Additional chart options merged with defaults */
  chartOptions?: DeepPartial<ChartOptions>;
  /** Callback when chart is ready - use to add series. Called once on mount. */
  onChartReady?: (chart: IChartApi) => void;
  /** Container height */
  height?: number | string;
  /** Additional container class names */
  className?: string;
}

export function LWChart({
  chartOptions,
  onChartReady,
  height = 300,
  className = '',
}: LWChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  // Store callback in ref to avoid recreating chart when callback changes
  const onChartReadyRef = useRef(onChartReady);
  onChartReadyRef.current = onChartReady;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Merge default options with custom options
    const options: DeepPartial<ChartOptions> = {
      ...lwcDefaultOptions,
      ...chartOptions,
      width: container.clientWidth,
      height: typeof height === 'number' ? height : undefined,
    };

    // Create the chart
    const chart = createChart(container, options);
    chartRef.current = chart;

    // Set up ResizeObserver for responsive sizing
    const resizeObserver = new ResizeObserver(() => {
      if (chartRef.current && container) {
        chartRef.current.applyOptions({
          width: container.clientWidth,
        });
      }
    });
    resizeObserver.observe(container);

    // Notify parent that chart is ready (use ref to get latest callback)
    onChartReadyRef.current?.(chart);

    // Cleanup
    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
    // Only recreate chart if chartOptions or height changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [height]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        height: typeof height === 'string' ? height : `${height}px`,
      }}
    />
  );
}
