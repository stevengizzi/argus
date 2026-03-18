/**
 * Timeline view — horizontal session timeline spanning 9:30 AM – 4:00 PM ET.
 *
 * One lane per strategy with events plotted as marks at severity levels.
 * Active strategy windows visually highlighted. Current time indicator in live mode.
 * Scroll/zoom to navigate and expand/compress the time scale.
 *
 * No charting library — pure div + SVG layout.
 *
 * Sprint 25, Session 8.
 */

import { useRef, useState, useCallback, useEffect } from 'react';
import { useTimelineData, STRATEGY_LANES } from '../hooks/useTimelineData';
import {
  TimelineLane,
  LANE_HEIGHT,
  MARKET_OPEN_MINUTES,
  MARKET_CLOSE_MINUTES,
  TOTAL_MINUTES,
} from './TimelineLane';

const MIN_PIXELS_PER_MINUTE = 1;
const MAX_PIXELS_PER_MINUTE = 20;
const DEFAULT_PIXELS_PER_MINUTE = 3;

/** Label offset for the strategy name column. */
const LABEL_WIDTH = 140;

/** Generate 30-minute tick marks from 9:30 to 16:00. */
function generateTimeTicks(): { minutes: number; label: string }[] {
  const ticks: { minutes: number; label: string }[] = [];
  for (let m = MARKET_OPEN_MINUTES; m <= MARKET_CLOSE_MINUTES; m += 30) {
    const hours = Math.floor(m / 60);
    const mins = m % 60;
    const hour12 = hours > 12 ? hours - 12 : hours;
    const ampm = hours >= 12 ? 'PM' : 'AM';
    ticks.push({
      minutes: m - MARKET_OPEN_MINUTES,
      label: `${hour12}:${mins.toString().padStart(2, '0')} ${ampm}`,
    });
  }
  return ticks;
}

const TIME_TICKS = generateTimeTicks();

interface TimelineViewProps {
  selectedSymbol: string | null;
  onSelectSymbol: (symbol: string) => void;
  date?: string;
}

export function TimelineView({
  selectedSymbol,
  onSelectSymbol,
  date,
}: TimelineViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pixelsPerMinute, setPixelsPerMinute] = useState(DEFAULT_PIXELS_PER_MINUTE);
  const isDebrief = date !== undefined;

  const { lanes, currentTime, isLoading } = useTimelineData({ date });

  const timelineWidth = TOTAL_MINUTES * pixelsPerMinute;

  // Mouse wheel zoom
  const handleWheel = useCallback(
    (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.3 : 0.3;
        setPixelsPerMinute((prev) =>
          Math.max(MIN_PIXELS_PER_MINUTE, Math.min(MAX_PIXELS_PER_MINUTE, prev + delta))
        );
      }
    },
    [],
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, [handleWheel]);

  // Current time indicator position
  const now = new Date(currentTime);
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  const nowX = (nowMinutes - MARKET_OPEN_MINUTES) * pixelsPerMinute;
  const showNowLine = !isDebrief && nowMinutes >= MARKET_OPEN_MINUTES && nowMinutes <= MARKET_CLOSE_MINUTES;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full" data-testid="timeline-loading">
        <span className="text-xs text-argus-text-dim">Loading timeline…</span>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="h-full overflow-x-auto overflow-y-hidden"
      data-testid="timeline-view"
    >
      <div style={{ minWidth: LABEL_WIDTH + timelineWidth + 20 }}>
        {/* Time axis header */}
        <div
          className="relative border-b border-argus-border"
          style={{ height: 28, paddingLeft: LABEL_WIDTH }}
          data-testid="timeline-time-axis"
        >
          <svg
            width={timelineWidth}
            height={28}
            viewBox={`0 0 ${timelineWidth} 28`}
          >
            {TIME_TICKS.map((tick) => {
              const x = tick.minutes * pixelsPerMinute;
              return (
                <g key={tick.minutes}>
                  <line
                    x1={x}
                    y1={18}
                    x2={x}
                    y2={28}
                    stroke="var(--color-border-secondary, #4a4a5a)"
                    strokeWidth={1}
                  />
                  <text
                    x={x}
                    y={14}
                    textAnchor="middle"
                    fill="var(--color-text-dim, #888)"
                    fontSize={9}
                    fontFamily="monospace"
                    data-testid="timeline-tick-label"
                  >
                    {tick.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Strategy lanes */}
        {lanes.map((lane) => (
          <TimelineLane
            key={lane.strategy.id}
            strategy={lane.strategy}
            events={lane.events}
            width={timelineWidth}
            pixelsPerMinute={pixelsPerMinute}
            onSelectSymbol={onSelectSymbol}
          />
        ))}

        {/* Current time indicator */}
        {showNowLine && (
          <div
            className="absolute top-0 h-full pointer-events-none z-20"
            style={{ left: LABEL_WIDTH + nowX, width: 1 }}
            data-testid="timeline-now-indicator"
          >
            <div className="w-px h-full bg-red-500/70" />
          </div>
        )}
      </div>
    </div>
  );
}
