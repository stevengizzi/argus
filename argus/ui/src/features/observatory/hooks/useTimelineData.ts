/**
 * Data hook for the Timeline view — fetches evaluation events per strategy,
 * classifies severity, and buckets into time intervals.
 *
 * In live mode: polls every 10s.
 * In debrief mode (date provided): fetches once, no polling.
 *
 * Sprint 25, Session 8.
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getStrategyDecisions } from '../../../api/client';
import type { EvaluationEvent } from '../../../api/types';

/** Strategy lane configuration. */
export interface StrategyLaneConfig {
  id: string;
  label: string;
  windowStart: string; // HH:MM format
  windowEnd: string;   // HH:MM format
}

export const STRATEGY_LANES: StrategyLaneConfig[] = [
  { id: 'orb_breakout', label: 'ORB Breakout', windowStart: '09:35', windowEnd: '11:30' },
  { id: 'orb_scalp', label: 'ORB Scalp', windowStart: '09:45', windowEnd: '11:30' },
  { id: 'vwap_reclaim', label: 'VWAP Reclaim', windowStart: '10:00', windowEnd: '12:00' },
  { id: 'afternoon_momentum', label: 'Afternoon Momentum', windowStart: '14:00', windowEnd: '15:30' },
];

/** Severity levels for timeline event marks. */
export type TimelineSeverity = 0 | 1 | 2 | 3;

/** Single bucketed event on the timeline. */
export interface TimelineEvent {
  time: string;        // ISO timestamp
  symbol: string;
  severity: TimelineSeverity;
  conditionsPassed?: number;
  conditionsTotal?: number;
  eventType: string;
  reason: string;
}

/** A single strategy lane with its events. */
export interface TimelineLaneData {
  strategy: StrategyLaneConfig;
  events: TimelineEvent[];
}

export interface UseTimelineDataResult {
  lanes: TimelineLaneData[];
  currentTime: string;
  isLoading: boolean;
}

/** Default bucket size in seconds for aggregation. */
const TIMELINE_BUCKET_SECONDS = 60;

/**
 * Classify an evaluation event into a severity level.
 *
 * 3 = trade executed, 2 = signal generated, 1 = near-miss (≥50% conditions passed), 0 = evaluation
 */
function classifySeverity(event: EvaluationEvent): TimelineSeverity {
  const eventType = event.event_type.toLowerCase();
  const result = event.result;

  if (eventType.includes('trade') || eventType.includes('fill')) return 3;
  if (eventType.includes('signal') || result === 'PASS') return 2;

  // Near-miss: check metadata for conditions_passed / conditions_total
  const passed = event.metadata?.conditions_passed;
  const total = event.metadata?.conditions_total;
  if (typeof passed === 'number' && typeof total === 'number' && total > 0) {
    if (passed / total >= 0.5) return 1;
  }

  return 0;
}

function toTimelineEvent(event: EvaluationEvent): TimelineEvent {
  const severity = classifySeverity(event);
  return {
    time: event.timestamp,
    symbol: event.symbol,
    severity,
    conditionsPassed: typeof event.metadata?.conditions_passed === 'number'
      ? event.metadata.conditions_passed as number
      : undefined,
    conditionsTotal: typeof event.metadata?.conditions_total === 'number'
      ? event.metadata.conditions_total as number
      : undefined,
    eventType: event.event_type,
    reason: event.reason,
  };
}

/**
 * Bucket events by rounding timestamps to bucket boundaries.
 * Within each bucket, keep only the highest-severity event per symbol.
 */
function bucketEvents(events: TimelineEvent[], bucketSeconds: number): TimelineEvent[] {
  if (events.length === 0) return [];

  const buckets = new Map<string, TimelineEvent>();

  for (const event of events) {
    const ts = new Date(event.time).getTime();
    const bucketKey = Math.floor(ts / (bucketSeconds * 1000));
    const key = `${bucketKey}:${event.symbol}`;

    const existing = buckets.get(key);
    if (!existing || event.severity > existing.severity) {
      buckets.set(key, event);
    }
  }

  return Array.from(buckets.values()).sort(
    (a, b) => new Date(a.time).getTime() - new Date(b.time).getTime()
  );
}

interface UseTimelineDataOptions {
  date?: string;
}

export function useTimelineData({ date }: UseTimelineDataOptions = {}): UseTimelineDataResult {
  const isDebrief = date !== undefined;

  // Fetch evaluation events for each strategy
  const orbBreakout = useQuery({
    queryKey: ['observatory', 'timeline', 'orb_breakout', date],
    queryFn: () => getStrategyDecisions('orb_breakout', { limit: 2000 }),
    refetchInterval: isDebrief ? false : 10_000,
  });

  const orbScalp = useQuery({
    queryKey: ['observatory', 'timeline', 'orb_scalp', date],
    queryFn: () => getStrategyDecisions('orb_scalp', { limit: 2000 }),
    refetchInterval: isDebrief ? false : 10_000,
  });

  const vwapReclaim = useQuery({
    queryKey: ['observatory', 'timeline', 'vwap_reclaim', date],
    queryFn: () => getStrategyDecisions('vwap_reclaim', { limit: 2000 }),
    refetchInterval: isDebrief ? false : 10_000,
  });

  const afternoonMomentum = useQuery({
    queryKey: ['observatory', 'timeline', 'afternoon_momentum', date],
    queryFn: () => getStrategyDecisions('afternoon_momentum', { limit: 2000 }),
    refetchInterval: isDebrief ? false : 10_000,
  });

  const queries = [orbBreakout, orbScalp, vwapReclaim, afternoonMomentum];
  const isLoading = queries.some((q) => q.isLoading);

  const lanes = useMemo<TimelineLaneData[]>(() => {
    const rawData = [
      orbBreakout.data,
      orbScalp.data,
      vwapReclaim.data,
      afternoonMomentum.data,
    ];

    return STRATEGY_LANES.map((strategy, i) => {
      const events = (rawData[i] ?? []).map(toTimelineEvent);
      return {
        strategy,
        events: bucketEvents(events, TIMELINE_BUCKET_SECONDS),
      };
    });
  }, [orbBreakout.data, orbScalp.data, vwapReclaim.data, afternoonMomentum.data]);

  const currentTime = new Date().toISOString();

  return { lanes, currentTime, isLoading };
}
