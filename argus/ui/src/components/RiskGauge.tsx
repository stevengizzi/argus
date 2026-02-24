/**
 * Radial gauge for risk utilization visualization.
 *
 * UX Feature Backlog item 17-C:
 * - SVG arc (270 degrees, gap at bottom)
 * - Background arc: zinc-700
 * - Fill arc animated, color transitions: green (0-50%), yellow (50-75%), red (75-100%)
 * - Center text: percentage value
 * - Label below gauge
 * - Framer Motion arc fill animation on mount
 * - Pulse animation when >90%
 */

import { motion } from 'framer-motion';
import { DURATION, EASE } from '../utils/motion';

interface RiskGaugeProps {
  label: string;
  value: number; // 0-100 percentage
  maxLabel?: string; // e.g., "3% daily limit"
  size?: 'sm' | 'md';
}

// Color thresholds
function getGaugeColor(value: number): string {
  if (value < 50) return '#22c55e'; // green-500
  if (value < 75) return '#eab308'; // yellow-500
  return '#ef4444'; // red-500
}

// SVG arc path calculation
function describeArc(
  x: number,
  y: number,
  radius: number,
  startAngle: number,
  endAngle: number
): string {
  const start = polarToCartesian(x, y, radius, endAngle);
  const end = polarToCartesian(x, y, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
}

function polarToCartesian(
  centerX: number,
  centerY: number,
  radius: number,
  angleInDegrees: number
): { x: number; y: number } {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180;
  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY + radius * Math.sin(angleInRadians),
  };
}

export function RiskGauge({ label, value, maxLabel, size = 'md' }: RiskGaugeProps) {
  const clampedValue = Math.max(0, Math.min(100, value));
  const color = getGaugeColor(clampedValue);
  const isPulsing = clampedValue >= 90;

  // Gauge dimensions
  const dimensions = size === 'sm' ? { width: 80, height: 80 } : { width: 100, height: 100 };
  const cx = dimensions.width / 2;
  const cy = dimensions.height / 2;
  const radius = (dimensions.width / 2) - 8; // Leave room for stroke
  const strokeWidth = size === 'sm' ? 6 : 8;

  // Arc spans 270 degrees (from 135 to 405, leaving 90 degree gap at bottom)
  const startAngle = 135;
  const totalAngle = 270;
  const endAngle = startAngle + totalAngle;
  const fillEndAngle = startAngle + (clampedValue / 100) * totalAngle;

  // Background arc (full 270 degrees)
  const bgPath = describeArc(cx, cy, radius, startAngle, endAngle);
  // Fill arc (proportional to value)
  const fillPath = clampedValue > 0 ? describeArc(cx, cy, radius, startAngle, fillEndAngle) : '';

  // Calculate stroke-dasharray and stroke-dashoffset for animation
  const circumference = 2 * Math.PI * radius * (totalAngle / 360);
  const fillLength = circumference * (clampedValue / 100);

  return (
    <div className="flex flex-col items-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: DURATION.normal, ease: EASE.out }}
        className="relative"
        style={{ width: dimensions.width, height: dimensions.height }}
      >
        <svg
          width={dimensions.width}
          height={dimensions.height}
          viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
        >
          {/* Background arc */}
          <path
            d={bgPath}
            fill="none"
            stroke="#3f3f46" // zinc-700
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Fill arc with animation */}
          {clampedValue > 0 && (
            <motion.path
              d={fillPath}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{
                pathLength: 1,
                opacity: isPulsing ? [1, 0.6, 1] : 1,
              }}
              transition={{
                pathLength: { duration: 0.5, ease: 'easeOut' },
                opacity: isPulsing
                  ? { duration: 1.5, repeat: Infinity, ease: 'easeInOut' }
                  : { duration: 0 },
              }}
              style={{
                strokeDasharray: fillLength,
                strokeDashoffset: 0,
              }}
            />
          )}
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={`font-bold text-argus-text ${
              size === 'sm' ? 'text-lg' : 'text-xl'
            }`}
          >
            {value > 0 ? `${Math.round(clampedValue)}%` : '—'}
          </span>
        </div>
      </motion.div>

      {/* Label */}
      <span className="mt-1 text-xs text-argus-text-dim text-center">{label}</span>
      {maxLabel && (
        <span className="text-xs text-argus-text-dim/60 text-center">{maxLabel}</span>
      )}
    </div>
  );
}
