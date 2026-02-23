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
 * @param durationMs - Animation duration in milliseconds (default 1600ms)
 * @param interpolate - Whether to interpolate partial points for smooth line drawing (default true).
 *                      Set to false for histogram series where interpolation doesn't make visual sense.
 */
export function animateChartDrawIn<T extends SeriesType>(
  series: ISeriesApi<T>,
  data: SeriesDataItemTypeMap[T][],
  chart: IChartApi,
  durationMs = 100,
  interpolate = true
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

    // Calculate continuous position in the data array
    const continuousIndex = easedProgress * (data.length - 1);
    const wholeIndex = Math.floor(continuousIndex);
    const fraction = continuousIndex - wholeIndex;

    // Include all complete data points up to wholeIndex
    const visibleData = data.slice(0, wholeIndex + 1);

    // Add interpolated point between current and next data point (line/area charts only)
    if (interpolate && wholeIndex < data.length - 1 && fraction > 0) {
      const current = data[wholeIndex];
      const next = data[wholeIndex + 1];

      // Interpolate the value (works for AreaData and other value-based series)
      const currentValue = (current as { value?: number }).value ?? 0;
      const nextValue = (next as { value?: number }).value ?? 0;
      const interpolatedValue = currentValue + (nextValue - currentValue) * fraction;

      visibleData.push({
        ...next,  // Use next point's time slot so chart doesn't create duplicate x
        value: interpolatedValue,
      } as SeriesDataItemTypeMap[T]);
    }

    series.setData(visibleData);

    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      // Ensure final frame shows exact data
      series.setData(data);
    }
  }

  requestAnimationFrame(step);
}
