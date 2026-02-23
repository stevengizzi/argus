/**
 * Progressive chart data reveal animation.
 *
 * Feeds data points in batches using requestAnimationFrame to create
 * a left-to-right draw-in effect. Uses fixed viewport (full time range
 * set upfront) so the chart doesn't zoom during animation.
 *
 * Stays within DEC-110 budget: <500ms, 60fps.
 */

import type { IChartApi, ISeriesApi, SeriesDataItemTypeMap } from 'lightweight-charts';

type SeriesType = keyof SeriesDataItemTypeMap;

/**
 * Animate chart data with a left-to-right draw-in effect.
 *
 * @param series - The Lightweight Charts series to animate
 * @param data - The full dataset to reveal progressively
 * @param chart - The chart instance (for fitting content)
 * @param durationMs - Animation duration in milliseconds (default 400ms)
 */
export function animateChartDrawIn<T extends SeriesType>(
  series: ISeriesApi<T>,
  data: SeriesDataItemTypeMap[T][],
  chart: IChartApi,
  durationMs = 400
): void {
  if (data.length === 0) return;

  // Set full data first to establish the time range, then fit content
  series.setData(data);
  chart.timeScale().fitContent();

  // Clear data to start animation from empty
  series.setData([]);

  const startTime = performance.now();

  function step(): void {
    const elapsed = performance.now() - startTime;
    const progress = Math.min(elapsed / durationMs, 1);
    // Ease-out cubic for natural deceleration
    const easedProgress = 1 - Math.pow(1 - progress, 3);

    const targetIndex = Math.max(1, Math.ceil(easedProgress * data.length));
    series.setData(data.slice(0, targetIndex));

    if (progress < 1) {
      requestAnimationFrame(step);
    }
  }

  requestAnimationFrame(step);
}
