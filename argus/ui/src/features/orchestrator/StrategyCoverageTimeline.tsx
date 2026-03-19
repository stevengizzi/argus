/**
 * Strategy Coverage Timeline - SVG visualization of strategy operating windows.
 *
 * Custom SVG component showing:
 * - Time axis with labels at major hours
 * - Vertical grid lines
 * - Per-strategy row with colored rect from earliest_entry to latest_entry
 * - "Now" marker at current ET time
 * - Throttled/paused strategies shown with reduced opacity
 *
 * Responsive:
 * - Desktop (>=1024px): full labels, time labels every 30min
 * - Tablet (640-1023px): medium labels, time labels every hour
 * - Mobile (<640px): single-letter labels, time labels every 2 hours
 */

import { useMemo, useState, useEffect } from 'react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import type { AllocationInfo } from '../../api/types';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { getStrategyDisplay, getStrategyColor } from '../../utils/strategyConfig';

interface StrategyCoverageTimelineProps {
  allocations: AllocationInfo[];
}

// Time constants (in minutes from midnight)
const MARKET_START_MIN = 570;  // 9:30 AM = 9*60 + 30
const MARKET_END_MIN = 960;    // 4:00 PM = 16*60
const TOTAL_MIN = MARKET_END_MIN - MARKET_START_MIN; // 390

// Time label positions
const TIME_LABELS_FULL = [
  { time: '9:30', min: 570 },
  { time: '10:00', min: 600 },
  { time: '10:30', min: 630 },
  { time: '11:00', min: 660 },
  { time: '11:30', min: 690 },
  { time: '12:00', min: 720 },
  { time: '12:30', min: 750 },
  { time: '1:00', min: 780 },
  { time: '1:30', min: 810 },
  { time: '2:00', min: 840 },
  { time: '2:30', min: 870 },
  { time: '3:00', min: 900 },
  { time: '3:30', min: 930 },
  { time: '4:00', min: 960 },
];

const TIME_LABELS_HOURLY = TIME_LABELS_FULL.filter((_, i) => i % 2 === 0);
const TIME_LABELS_2HOUR = TIME_LABELS_FULL.filter((_, i) => i % 4 === 0);

function timeToPercent(timeStr: string): number {
  const [h, m] = timeStr.split(':').map(Number);
  const totalMin = h * 60 + m;
  return ((totalMin - MARKET_START_MIN) / TOTAL_MIN) * 100;
}

function getCurrentETMinutes(): number {
  const now = new Date();
  // Convert to ET
  const etTime = now.toLocaleString('en-US', { timeZone: 'America/New_York' });
  const etDate = new Date(etTime);
  return etDate.getHours() * 60 + etDate.getMinutes();
}

function formatCurrentTime(): string {
  const now = new Date();
  return now.toLocaleTimeString('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: '2-digit'
  });
}

export function StrategyCoverageTimeline({ allocations }: StrategyCoverageTimelineProps) {
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const isTablet = useMediaQuery('(min-width: 640px)');

  // Current time state (updates every minute)
  const [currentMin, setCurrentMin] = useState(getCurrentETMinutes);
  const [currentTimeStr, setCurrentTimeStr] = useState(formatCurrentTime);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMin(getCurrentETMinutes());
      setCurrentTimeStr(formatCurrentTime());
    }, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  // Compute layout dimensions
  const layout = useMemo(() => {
    const labelWidth = isDesktop ? 140 : isTablet ? 60 : 32;
    const rowHeight = 28;
    const axisHeight = 24;
    const padding = 8;
    const numStrategies = allocations.length || 4; // Default to 4 for skeleton
    const totalHeight = axisHeight + (numStrategies * rowHeight) + padding;
    const timeLabels = isDesktop ? TIME_LABELS_FULL : isTablet ? TIME_LABELS_HOURLY : TIME_LABELS_2HOUR;

    return { labelWidth, rowHeight, axisHeight, padding, totalHeight, timeLabels };
  }, [isDesktop, isTablet, allocations.length]);

  // Filter to strategies with operating windows
  const strategiesWithWindows = useMemo(() => {
    return allocations.filter(a => a.operating_window !== null);
  }, [allocations]);

  // Compute now marker position
  const nowPercent = useMemo(() => {
    if (currentMin < MARKET_START_MIN || currentMin > MARKET_END_MIN) {
      return null; // Outside market hours
    }
    return ((currentMin - MARKET_START_MIN) / TOTAL_MIN) * 100;
  }, [currentMin]);

  // Check if market is currently open
  const isMarketHours = nowPercent !== null;

  const chartWidth = `calc(100% - ${layout.labelWidth}px)`;

  if (strategiesWithWindows.length === 0) {
    return (
      <Card>
        <CardHeader title="Strategy Coverage" subtitle="Operating windows" />
        <div className="flex items-center justify-center h-32 text-sm text-argus-text-dim">
          No operating window data available
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader title="Strategy Coverage" subtitle="Operating windows" />
      <div className="relative" style={{ height: layout.totalHeight }}>
        {/* Time axis labels */}
        <div
          className="absolute top-0 flex justify-between text-[10px] text-argus-text-dim"
          style={{ left: layout.labelWidth, width: chartWidth, height: layout.axisHeight }}
        >
          {layout.timeLabels.map((tl) => {
            const pct = ((tl.min - MARKET_START_MIN) / TOTAL_MIN) * 100;
            return (
              <span
                key={tl.time}
                className="absolute transform -translate-x-1/2 tabular-nums"
                style={{ left: `${pct}%` }}
              >
                {tl.time}
              </span>
            );
          })}
        </div>

        {/* SVG chart area */}
        <svg
          className="absolute"
          style={{
            top: layout.axisHeight,
            left: layout.labelWidth,
            width: chartWidth,
            height: layout.totalHeight - layout.axisHeight,
          }}
          preserveAspectRatio="none"
        >
          {/* Define striped pattern for throttled strategies */}
          <defs>
            <pattern
              id="throttled-stripes"
              patternUnits="userSpaceOnUse"
              width="8"
              height="8"
              patternTransform="rotate(45)"
            >
              <line x1="0" y1="0" x2="0" y2="8" stroke="currentColor" strokeWidth="2" />
            </pattern>
          </defs>

          {/* Vertical grid lines */}
          {layout.timeLabels.map((tl) => {
            const pct = ((tl.min - MARKET_START_MIN) / TOTAL_MIN) * 100;
            return (
              <line
                key={`grid-${tl.time}`}
                x1={`${pct}%`}
                y1="0"
                x2={`${pct}%`}
                y2="100%"
                stroke="#374151"
                strokeWidth="1"
                strokeDasharray="2,4"
              />
            );
          })}

          {/* Strategy bars */}
          {strategiesWithWindows.map((alloc, idx) => {
            const window = alloc.operating_window!;
            const startPct = timeToPercent(window.earliest_entry);
            const endPct = timeToPercent(window.latest_entry);
            const color = getStrategyColor(alloc.strategy_id);
            const isSuspended = !alloc.is_active;
            const isThrottledOrSuspended = alloc.is_throttled || isSuspended;
            const y = idx * layout.rowHeight + 4;
            const barHeight = layout.rowHeight - 8;

            return (
              <g key={alloc.strategy_id}>
                {/* Main bar */}
                <rect
                  x={`${startPct}%`}
                  y={y}
                  width={`${endPct - startPct}%`}
                  height={barHeight}
                  fill={color}
                  opacity={isThrottledOrSuspended ? 0.3 : 0.8}
                  rx={4}
                />
                {/* Stripe overlay for throttled/suspended */}
                {isThrottledOrSuspended && (
                  <rect
                    x={`${startPct}%`}
                    y={y}
                    width={`${endPct - startPct}%`}
                    height={barHeight}
                    fill="url(#throttled-stripes)"
                    opacity={0.3}
                    rx={4}
                    className="text-gray-500"
                  />
                )}
              </g>
            );
          })}

          {/* Now marker */}
          {isMarketHours && nowPercent !== null && (
            <g>
              <line
                x1={`${nowPercent}%`}
                y1="0"
                x2={`${nowPercent}%`}
                y2="100%"
                stroke="#ef4444"
                strokeWidth="2"
                strokeDasharray="4,4"
              />
            </g>
          )}
        </svg>

        {/* Strategy labels (left side) */}
        <div
          className="absolute top-0 flex flex-col"
          style={{
            top: layout.axisHeight,
            left: 0,
            width: layout.labelWidth - 8,
          }}
        >
          {strategiesWithWindows.map((alloc) => {
            const config = getStrategyDisplay(alloc.strategy_id);
            const label = isDesktop ? config.name : isTablet ? config.shortName : config.letter;
            const color = config.color;
            const isSuspended = !alloc.is_active;
            const isThrottledOrSuspended = alloc.is_throttled || isSuspended;

            // Build status suffix for desktop labels
            let statusSuffix = '';
            if (isDesktop) {
              if (isSuspended) statusSuffix = ' (Susp)';
              else if (alloc.is_throttled) statusSuffix = ' (Thrt)';
            }

            return (
              <div
                key={alloc.strategy_id}
                className={`flex items-center justify-end pr-2 text-xs font-medium truncate ${
                  isThrottledOrSuspended ? 'opacity-50' : ''
                }`}
                style={{
                  height: layout.rowHeight,
                  color,
                }}
                title={isSuspended ? 'Suspended (circuit breaker)' : alloc.is_throttled ? 'Throttled' : undefined}
              >
                {label}{statusSuffix}
              </div>
            );
          })}
        </div>

        {/* Now time label (below chart) */}
        {isMarketHours && nowPercent !== null && (
          <div
            className="absolute text-[10px] text-argus-loss font-medium transform -translate-x-1/2"
            style={{
              left: `calc(${layout.labelWidth}px + ${nowPercent}% * (100% - ${layout.labelWidth}px) / 100%)`,
              top: layout.totalHeight - 4,
            }}
          >
            Now
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-end gap-4 mt-2 text-[10px] text-argus-text-dim">
        {isMarketHours && (
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-argus-loss" style={{ borderTop: '2px dashed #ef4444' }} />
            <span>Now ({currentTimeStr})</span>
          </span>
        )}
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 bg-gray-500/30 rounded" />
          <span>Throttled / Suspended</span>
        </span>
      </div>
    </Card>
  );
}
