/**
 * Lightweight SVG sparkline for ambient trend visualization.
 *
 * Renders a simple line chart with optional area fill below.
 * No axes, labels, or tooltips — pure ambient visualization.
 * Auto-measures container width using ResizeObserver for responsive sizing.
 *
 * Edge cases:
 * - Empty array: renders nothing
 * - Single point: horizontal line at center
 * - All same values: horizontal line at center
 */

import { useMemo, useRef, useState, useEffect } from 'react';

interface SparklineProps {
  /** Array of numeric values to plot */
  data: number[];
  /** SVG height in pixels (default 40) */
  height?: number;
  /** Line/fill color - CSS color value or Tailwind variable (default argus-accent) */
  color?: string;
  /** Opacity of the area fill below the line (default 0.1) */
  fillOpacity?: number;
  /** Line stroke width (default 1.5) */
  strokeWidth?: number;
  /** Additional CSS classes for the container */
  className?: string;
}

export function Sparkline({
  data,
  height = 40,
  color = 'var(--color-argus-accent)',
  fillOpacity = 0.1,
  strokeWidth = 1.5,
  className = '',
}: SparklineProps) {
  // Auto-measure container width
  const containerRef = useRef<HTMLDivElement>(null);
  const [measuredWidth, setMeasuredWidth] = useState(120); // fallback

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setMeasuredWidth(Math.round(entry.contentRect.width));
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const { polylinePoints, polygonPoints } = useMemo(() => {
    // Edge case: empty array
    if (data.length === 0) {
      return { polylinePoints: '', polygonPoints: '' };
    }

    // Add padding to keep line from touching edges
    const paddingY = 4;
    const paddingX = 2;
    const chartWidth = measuredWidth - paddingX * 2;
    const chartHeight = height - paddingY * 2;

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min;

    // Edge case: single point or all same values - draw horizontal line at center
    if (data.length === 1 || range === 0) {
      const y = paddingY + chartHeight / 2;
      const startX = paddingX;
      const endX = measuredWidth - paddingX;

      const linePoints = `${startX},${y} ${endX},${y}`;
      const areaPoints = `${startX},${height} ${startX},${y} ${endX},${y} ${endX},${height}`;

      return { polylinePoints: linePoints, polygonPoints: areaPoints };
    }

    // Calculate points for multiple values
    const xStep = chartWidth / (data.length - 1);
    const points = data.map((value, i) => {
      const x = paddingX + i * xStep;
      // Normalize value to chart height (invert Y since SVG Y grows downward)
      const normalizedValue = (value - min) / range;
      const y = paddingY + chartHeight * (1 - normalizedValue);
      return { x, y };
    });

    // Generate polyline points string
    const linePoints = points.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ');

    // Generate polygon points for area fill (includes bottom edge)
    const firstPoint = points[0];
    const lastPoint = points[points.length - 1];
    const bottomY = height;
    const areaPoints = [
      `${firstPoint.x.toFixed(2)},${bottomY}`, // Bottom-left
      ...points.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`), // Line points
      `${lastPoint.x.toFixed(2)},${bottomY}`, // Bottom-right
    ].join(' ');

    return { polylinePoints: linePoints, polygonPoints: areaPoints };
  }, [data, measuredWidth, height]);

  // Don't render anything if no data
  if (data.length === 0) {
    return null;
  }

  return (
    <div ref={containerRef} className={className} style={{ width: '100%' }}>
      <svg
        width={measuredWidth}
        height={height}
        viewBox={`0 0 ${measuredWidth} ${height}`}
        aria-hidden="true"
      >
        {/* Area fill - use style to resolve CSS variables with smooth color transition */}
        <polygon
          points={polygonPoints}
          style={{
            fill: color,
            fillOpacity,
            transition: 'fill 300ms ease-in-out',
          }}
        />
        {/* Line - use style to resolve CSS variables with smooth color transition */}
        <polyline
          points={polylinePoints}
          style={{
            fill: 'none',
            stroke: color,
            strokeWidth,
            strokeLinecap: 'round',
            strokeLinejoin: 'round',
            transition: 'stroke 300ms ease-in-out',
          }}
        />
      </svg>
    </div>
  );
}
