/**
 * Single strategy lane for the Timeline view.
 *
 * Renders event marks positioned along the time axis at 4 severity levels:
 * - Evaluation (0): tiny dot, low opacity
 * - Near-miss (1): medium dot, purple
 * - Signal (2): larger dot, amber
 * - Trade (3): largest dot, green
 *
 * Dense evaluation dots aggregate into count badges when zoomed out.
 *
 * Sprint 25, Session 8.
 */

import { useMemo, useState, useCallback } from 'react';
import type { TimelineEvent, TimelineSeverity, StrategyLaneConfig } from '../hooks/useTimelineData';

/** Timeline spans 9:30 AM to 4:00 PM ET = 390 minutes. */
const MARKET_OPEN_MINUTES = 9 * 60 + 30;  // 570
const MARKET_CLOSE_MINUTES = 16 * 60;      // 960
const TOTAL_MINUTES = MARKET_CLOSE_MINUTES - MARKET_OPEN_MINUTES; // 390

const LANE_HEIGHT = 60;

/** Severity visual config. */
const SEVERITY_CONFIG: Record<TimelineSeverity, { color: string; size: number; opacity: number; label: string }> = {
  0: { color: 'var(--color-border-secondary, #4a4a5a)', size: 3, opacity: 0.3, label: 'Evaluation' },
  1: { color: '#7F77DD', size: 5, opacity: 0.7, label: 'Near-miss' },
  2: { color: '#EF9F27', size: 7, opacity: 0.9, label: 'Signal' },
  3: { color: '#1D9E75', size: 10, opacity: 1.0, label: 'Trade' },
};

/** Max events per pixel before aggregation kicks in. */
const AGGREGATION_THRESHOLD = 20;

interface TimelineLaneProps {
  strategy: StrategyLaneConfig;
  events: TimelineEvent[];
  width: number;
  pixelsPerMinute: number;
  onSelectSymbol: (symbol: string) => void;
}

/** Convert a timestamp to x-position in the timeline. */
function timeToX(timestamp: string, pixelsPerMinute: number): number {
  const date = new Date(timestamp);
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const totalMinutes = hours * 60 + minutes;
  const minutesSinceOpen = totalMinutes - MARKET_OPEN_MINUTES;
  return Math.max(0, minutesSinceOpen * pixelsPerMinute);
}

/** Convert window time string (HH:MM) to x-position. */
function windowTimeToX(timeStr: string, pixelsPerMinute: number): number {
  const [hours, minutes] = timeStr.split(':').map(Number);
  const totalMinutes = hours * 60 + minutes;
  const minutesSinceOpen = totalMinutes - MARKET_OPEN_MINUTES;
  return Math.max(0, minutesSinceOpen * pixelsPerMinute);
}

interface AggregatedCluster {
  x: number;
  count: number;
  severity: TimelineSeverity;
  events: TimelineEvent[];
}

/**
 * Aggregate dense evaluation dots (severity 0) into clusters.
 * Higher severity events are always rendered individually.
 */
function aggregateEvents(
  events: TimelineEvent[],
  pixelsPerMinute: number,
  width: number,
): { individual: TimelineEvent[]; clusters: AggregatedCluster[] } {
  const individual: TimelineEvent[] = [];
  const evalEvents: TimelineEvent[] = [];

  for (const event of events) {
    if (event.severity > 0) {
      individual.push(event);
    } else {
      evalEvents.push(event);
    }
  }

  // Check if evaluation events are dense enough to warrant aggregation
  if (evalEvents.length <= AGGREGATION_THRESHOLD || width <= 0) {
    return { individual: [...individual, ...evalEvents], clusters: [] };
  }

  // Bucket eval events into pixel-width buckets (~10px each)
  const bucketMap = new Map<number, TimelineEvent[]>();

  for (const event of evalEvents) {
    const x = timeToX(event.time, pixelsPerMinute);
    const bucketKey = Math.floor(x / 10);
    const existing = bucketMap.get(bucketKey);
    if (existing) {
      existing.push(event);
    } else {
      bucketMap.set(bucketKey, [event]);
    }
  }

  const clusters: AggregatedCluster[] = [];
  for (const [bucketKey, bucketEvents] of bucketMap) {
    if (bucketEvents.length > AGGREGATION_THRESHOLD) {
      clusters.push({
        x: bucketKey * 10 + 5, // center of bucket
        count: bucketEvents.length,
        severity: 0,
        events: bucketEvents,
      });
    } else {
      individual.push(...bucketEvents);
    }
  }

  return { individual, clusters };
}

export function TimelineLane({
  strategy,
  events,
  width,
  pixelsPerMinute,
  onSelectSymbol,
}: TimelineLaneProps) {
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    content: string;
  } | null>(null);

  const activeWindowStart = windowTimeToX(strategy.windowStart, pixelsPerMinute);
  const activeWindowEnd = windowTimeToX(strategy.windowEnd, pixelsPerMinute);
  const activeWindowWidth = activeWindowEnd - activeWindowStart;

  const { individual, clusters } = useMemo(
    () => aggregateEvents(events, pixelsPerMinute, width),
    [events, pixelsPerMinute, width],
  );

  const handleEventHover = useCallback(
    (event: TimelineEvent, clientX: number, clientY: number) => {
      const time = new Date(event.time).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
      const severityLabel = SEVERITY_CONFIG[event.severity].label;
      const conditions = event.conditionsPassed !== undefined && event.conditionsTotal !== undefined
        ? ` (${event.conditionsPassed}/${event.conditionsTotal})`
        : '';
      setTooltip({
        x: clientX,
        y: clientY,
        content: `${event.symbol} · ${time} · ${severityLabel}${conditions}`,
      });
    },
    [],
  );

  const handleMouseLeave = useCallback(() => setTooltip(null), []);

  const handleEventClick = useCallback(
    (event: TimelineEvent) => {
      onSelectSymbol(event.symbol);
    },
    [onSelectSymbol],
  );

  return (
    <div
      className="relative border-b border-argus-border"
      style={{ height: LANE_HEIGHT }}
      data-testid={`timeline-lane-${strategy.id}`}
      onMouseLeave={handleMouseLeave}
    >
      {/* Strategy label */}
      <div
        className="absolute left-0 top-0 z-10 flex items-center h-full pl-2"
        style={{ width: 140 }}
      >
        <span
          className="text-[10px] font-semibold text-argus-text-dim uppercase tracking-wider truncate"
          data-testid={`timeline-lane-label-${strategy.id}`}
        >
          {strategy.label}
        </span>
      </div>

      {/* Active window highlight */}
      <div
        className="absolute top-0 h-full bg-argus-accent/5"
        style={{
          left: 140 + activeWindowStart,
          width: activeWindowWidth,
        }}
        data-testid={`timeline-active-window-${strategy.id}`}
      />

      {/* Event marks */}
      <svg
        className="absolute top-0 left-0 h-full"
        style={{ left: 140, width: width }}
        viewBox={`0 0 ${width} ${LANE_HEIGHT}`}
        preserveAspectRatio="none"
      >
        {/* Individual event dots */}
        {individual.map((event, i) => {
          const x = timeToX(event.time, pixelsPerMinute);
          const config = SEVERITY_CONFIG[event.severity];
          return (
            <circle
              key={`${event.symbol}-${event.time}-${i}`}
              cx={x}
              cy={LANE_HEIGHT / 2}
              r={config.size / 2}
              fill={config.color}
              opacity={config.opacity}
              className="cursor-pointer"
              data-testid={`timeline-event-${event.severity}`}
              onMouseEnter={(e) => handleEventHover(event, e.clientX, e.clientY)}
              onClick={() => handleEventClick(event)}
            />
          );
        })}

        {/* Aggregated clusters */}
        {clusters.map((cluster, i) => (
          <g key={`cluster-${i}`}>
            <rect
              x={cluster.x - 8}
              y={LANE_HEIGHT / 2 - 8}
              width={16}
              height={16}
              rx={3}
              fill="var(--color-border-secondary, #4a4a5a)"
              opacity={0.4}
              className="cursor-default"
            />
            <text
              x={cluster.x}
              y={LANE_HEIGHT / 2 + 4}
              textAnchor="middle"
              fill="var(--color-text-dim, #888)"
              fontSize={9}
              fontFamily="monospace"
              data-testid="timeline-cluster-badge"
            >
              {cluster.count}
            </text>
          </g>
        ))}
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 px-2 py-1 rounded bg-argus-surface-2 border border-argus-border shadow-lg text-[10px] text-argus-text whitespace-nowrap pointer-events-none"
          style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
          data-testid="timeline-tooltip"
        >
          {tooltip.content}
        </div>
      )}
    </div>
  );
}

export { LANE_HEIGHT, MARKET_OPEN_MINUTES, MARKET_CLOSE_MINUTES, TOTAL_MINUTES, SEVERITY_CONFIG };
