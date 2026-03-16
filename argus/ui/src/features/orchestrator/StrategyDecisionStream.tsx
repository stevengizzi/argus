/**
 * Strategy Decision Stream — live-scrolling evaluation event log.
 *
 * Shows evaluation events for a selected strategy with color coding,
 * symbol filtering, summary stats, and expandable metadata.
 *
 * Sprint 24.5 Session 4.
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronDown, ChevronRight } from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { useStrategyDecisions } from '../../hooks/useStrategyDecisions';
import type { EvaluationEvent } from '../../hooks/useStrategyDecisions';
import { staggerContainer, staggerItem } from '../../utils/motion';

interface StrategyDecisionStreamProps {
  strategyId: string;
  onClose: () => void;
}

function resultColor(event: EvaluationEvent): string {
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

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'America/New_York',
  });
}

function EventRow({ event }: { event: EvaluationEvent }) {
  const [expanded, setExpanded] = useState(false);
  const hasMetadata = Object.keys(event.metadata).length > 0;

  return (
    <div data-testid="event-row">
      <div
        className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-argus-surface-2 transition-colors cursor-pointer"
        onClick={() => hasMetadata && setExpanded(!expanded)}
        data-testid="event-row-header"
      >
        {hasMetadata ? (
          expanded ? (
            <ChevronDown className="w-3 h-3 text-argus-text-dim shrink-0" />
          ) : (
            <ChevronRight className="w-3 h-3 text-argus-text-dim shrink-0" />
          )
        ) : (
          <span className="w-3 shrink-0" />
        )}

        <span className="text-xs text-argus-text-dim tabular-nums w-16 shrink-0">
          {formatTimestamp(event.timestamp)}
        </span>

        <span className="text-xs font-medium text-argus-text bg-argus-surface-2 px-1.5 py-0.5 rounded shrink-0">
          {event.symbol}
        </span>

        <span className="text-xs text-argus-text-dim truncate w-28 shrink-0" data-testid="event-type">
          {event.event_type}
        </span>

        <span className={`text-xs font-medium shrink-0 ${resultColor(event)}`} data-testid="event-result">
          {event.result}
        </span>

        <span
          className="text-xs text-argus-text-dim truncate flex-1 min-w-0"
          title={event.reason}
        >
          {event.reason}
        </span>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <pre
              className="text-xs text-argus-text-dim bg-argus-surface-2/50 px-4 py-2 mx-2 mb-1 rounded overflow-x-auto"
              data-testid="event-metadata"
            >
              {JSON.stringify(event.metadata, null, 2)}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function StrategyDecisionStream({ strategyId, onClose }: StrategyDecisionStreamProps) {
  const [symbolFilter, setSymbolFilter] = useState<string>('');
  const { data, isLoading, error } = useStrategyDecisions(strategyId, {
    symbol: symbolFilter || undefined,
    limit: 200,
  });

  const events = data ?? [];

  const uniqueSymbols = useMemo(
    () => [...new Set(events.map((e) => e.symbol))].sort(),
    [events]
  );

  const filteredEvents = useMemo(
    () => (symbolFilter ? events.filter((e) => e.symbol === symbolFilter) : events),
    [events, symbolFilter]
  );

  const signalCount = useMemo(
    () => filteredEvents.filter((e) => e.event_type === 'SIGNAL_GENERATED').length,
    [filteredEvents]
  );

  const rejectedCount = useMemo(
    () => filteredEvents.filter((e) => e.event_type === 'SIGNAL_REJECTED').length,
    [filteredEvents]
  );

  return (
    <div data-testid="strategy-decision-stream">
      <CardHeader
        title={strategyId}
        action={
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-argus-surface-2 transition-colors"
            aria-label="Close decision stream"
            data-testid="close-button"
          >
            <X className="w-4 h-4 text-argus-text-dim" />
          </button>
        }
      />
      <Card>
        {/* Symbol filter */}
        <div className="flex items-center gap-3 mb-3">
          <select
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            className="text-xs bg-argus-surface-2 border border-argus-border rounded px-2 py-1 text-argus-text"
            data-testid="symbol-filter"
          >
            <option value="">All symbols</option>
            {uniqueSymbols.map((sym) => (
              <option key={sym} value={sym}>
                {sym}
              </option>
            ))}
          </select>

          {/* Summary stats */}
          <div className="flex items-center gap-4 text-xs text-argus-text-dim" data-testid="summary-stats">
            <span>Symbols: {uniqueSymbols.length}</span>
            <span>Signals: {signalCount}</span>
            <span>Rejected: {rejectedCount}</span>
          </div>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="space-y-2" data-testid="loading-skeleton">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-7 bg-argus-surface-2 rounded animate-pulse" />
            ))}
          </div>
        )}

        {/* Error state */}
        {error && !isLoading && (
          <div className="flex items-center justify-center h-32" data-testid="error-state">
            <p className="text-sm text-red-400">
              Failed to load decisions: {error.message}
            </p>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && filteredEvents.length === 0 && (
          <div
            className="flex items-center justify-center h-32"
            data-testid="empty-state"
          >
            <p className="text-sm text-argus-text-dim">
              Awaiting market data — evaluation events will appear when strategies
              begin processing candles.
            </p>
          </div>
        )}

        {/* Event list */}
        {!isLoading && !error && filteredEvents.length > 0 && (
          <motion.div
            variants={staggerContainer(0.03)}
            initial="hidden"
            animate="show"
            className="max-h-96 overflow-y-auto space-y-0.5"
            data-testid="event-list"
          >
            {filteredEvents.map((event, idx) => (
              <motion.div key={`${event.timestamp}-${event.symbol}-${idx}`} variants={staggerItem}>
                <EventRow event={event} />
              </motion.div>
            ))}
          </motion.div>
        )}
      </Card>
    </div>
  );
}
