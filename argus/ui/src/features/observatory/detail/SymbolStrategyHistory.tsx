/**
 * Chronological strategy evaluation history for the Observatory detail panel.
 *
 * Shows all evaluation events for a symbol today across all strategies.
 * Events sorted newest-first. Color-coded using the Sprint 24.5 Decision Stream palette:
 * - PASS: emerald-400
 * - FAIL: red-400
 * - INFO: amber-400
 * - SIGNAL_GENERATED / QUALITY_SCORED: blue-400
 *
 * Data source: /api/v1/observatory/symbol/{symbol}/journey
 */

import type { ObservatoryJourneyEvent } from '../../../api/client';

interface SymbolStrategyHistoryProps {
  events: ObservatoryJourneyEvent[];
}

function resultColor(event: ObservatoryJourneyEvent): string {
  if (event.event_type === 'SIGNAL_GENERATED' || event.event_type === 'QUALITY_SCORED') {
    return 'text-blue-400';
  }
  switch (event.result) {
    case 'PASS':
      return 'text-emerald-400';
    case 'FAIL':
      return 'text-red-400';
    case 'INFO':
      return 'text-amber-400';
    default:
      return 'text-argus-text-dim';
  }
}

function formatTimestamp(isoTimestamp: string): string {
  try {
    const date = new Date(isoTimestamp);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return isoTimestamp;
  }
}

function formatEventType(eventType: string): string {
  return eventType.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
}

export function SymbolStrategyHistory({ events }: SymbolStrategyHistoryProps) {
  const sortedEvents = [...events].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  if (sortedEvents.length === 0) {
    return (
      <div className="text-xs text-argus-text-dim" data-testid="strategy-history-empty">
        No evaluation history for today
      </div>
    );
  }

  return (
    <div
      className="space-y-0.5 max-h-64 overflow-y-auto"
      data-testid="strategy-history"
    >
      {sortedEvents.map((event, idx) => (
        <div
          key={`${event.timestamp}-${event.strategy}-${idx}`}
          className="flex items-start gap-2 px-2 py-1 rounded text-[11px] hover:bg-argus-surface-2/30"
          data-testid="history-event"
        >
          <span className="text-argus-text-dim font-mono shrink-0 w-[60px]">
            {formatTimestamp(event.timestamp)}
          </span>
          <span className="text-argus-text-dim shrink-0 w-[48px] truncate text-[10px]">
            {event.strategy}
          </span>
          <span className={`shrink-0 w-[20px] text-center font-semibold ${resultColor(event)}`}>
            {event.result === 'PASS' ? '+' : event.result === 'FAIL' ? '-' : '*'}
          </span>
          <span className="text-argus-text truncate min-w-0">
            {formatEventType(event.event_type)}
            {event.metadata?.reason ? ` — ${String(event.metadata.reason)}` : ''}
          </span>
        </div>
      ))}
    </div>
  );
}
