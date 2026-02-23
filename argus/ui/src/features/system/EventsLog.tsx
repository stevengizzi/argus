/**
 * WebSocket events log.
 *
 * Collapsible section showing last 20 events with colored type badges,
 * sequence numbers, timestamps, and truncated data.
 * Always expanded by default (both mobile and desktop).
 */

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Trash2 } from 'lucide-react';
import { Card } from '../../components/Card';
import { Badge } from '../../components/Badge';
import { useLiveStore } from '../../stores/live';
import { formatTime } from '../../utils/format';
import { DURATION, EASE } from '../../utils/motion';
import type { WebSocketMessage } from '../../api/types';

const MAX_DISPLAY_EVENTS = 20;

type EventVariant = 'info' | 'success' | 'warning' | 'danger' | 'neutral';

function getEventBadgeVariant(type: string): EventVariant {
  // Position events
  if (type.startsWith('position.')) return 'info';

  // Order events
  if (type === 'order.filled') return 'success';
  if (type === 'order.rejected' || type === 'order.cancelled') return 'danger';
  if (type.startsWith('order.')) return 'info';

  // System events
  if (type === 'system.circuit_breaker') return 'danger';
  if (type === 'system.heartbeat') return 'neutral';
  if (type.startsWith('system.')) return 'warning';

  // Price updates
  if (type === 'price.update') return 'neutral';

  // Strategy events
  if (type === 'strategy.signal') return 'info';

  // Scanner
  if (type === 'scanner.watchlist') return 'info';

  return 'neutral';
}

function truncateData(data: unknown, maxLength: number = 60): string {
  if (data === null || data === undefined) return '';

  let str: string;
  if (typeof data === 'object') {
    str = JSON.stringify(data);
  } else {
    str = String(data);
  }

  if (str.length > maxLength) {
    return str.substring(0, maxLength) + '...';
  }
  return str;
}

function formatEventType(type: string): string {
  // Shorten common event types for display
  return type
    .replace('position.', 'pos.')
    .replace('system.', 'sys.')
    .replace('strategy.', 'strat.')
    .replace('scanner.', 'scan.')
    .replace('price.update', 'price');
}

interface EventRowProps {
  event: WebSocketMessage;
}

function EventRow({ event }: EventRowProps) {
  const variant = getEventBadgeVariant(event.type);
  const dataPreview = truncateData(event.data);

  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-argus-border last:border-b-0 text-xs">
      <Badge variant={variant}>
        {formatEventType(event.type)}
      </Badge>
      <span className="text-argus-text-dim shrink-0">
        #{event.sequence}
      </span>
      <span className="text-argus-text-dim shrink-0 tabular-nums">
        {formatTime(event.timestamp)}
      </span>
      {dataPreview && (
        <span className="text-argus-text-dim truncate flex-1 font-mono">
          {dataPreview}
        </span>
      )}
    </div>
  );
}

export function EventsLog() {
  const recentEvents = useLiveStore((state) => state.recentEvents);
  const clearEvents = useLiveStore((state) => state.clearEvents);
  const connected = useLiveStore((state) => state.connected);

  // Always expanded by default (both mobile and desktop)
  const [isExpanded, setIsExpanded] = useState(true);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to top (newest) when new events arrive
  useEffect(() => {
    if (isExpanded && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [recentEvents, isExpanded]);

  // Get the last 20 events for display
  const displayEvents = recentEvents.slice(0, MAX_DISPLAY_EVENTS);
  const eventCount = recentEvents.length;

  return (
    <Card noPadding>
      {/* Collapsible header - fixed height regardless of expanded state */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 h-[60px] hover:bg-argus-surface-2 transition-colors"
      >
        <div className="flex items-center gap-2">
          {/* Animated chevron */}
          <motion.span
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: DURATION.fast, ease: EASE.out }}
          >
            <ChevronDown className="w-4 h-4 text-argus-text-dim" />
          </motion.span>
          <span className="text-sm font-medium uppercase tracking-wider text-argus-text-dim">
            Recent Events
          </span>
          <span className="text-xs text-argus-text-dim">
            ({eventCount})
          </span>
          {/* Connection indicator */}
          <span
            className={`inline-block w-1.5 h-1.5 rounded-full ${
              connected ? 'bg-argus-profit' : 'bg-argus-loss'
            }`}
          />
        </div>

        {/* Clear button - always rendered but visibility controlled */}
        <motion.button
          onClick={(e) => {
            e.stopPropagation();
            clearEvents();
          }}
          className="flex items-center justify-center gap-1.5 px-3 min-h-[44px] text-xs text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-3 rounded transition-colors"
          aria-label="Clear events"
          initial={false}
          animate={{
            opacity: isExpanded && eventCount > 0 ? 1 : 0,
            pointerEvents: isExpanded && eventCount > 0 ? 'auto' : 'none',
          }}
          transition={{ duration: DURATION.fast }}
        >
          <Trash2 className="w-3.5 h-3.5" />
          Clear
        </motion.button>
      </button>

      {/* Animated event list */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: DURATION.normal, ease: EASE.out }}
            className="overflow-hidden"
          >
            <div
              ref={scrollRef}
              className="px-4 pb-4 max-h-64 overflow-y-auto"
            >
              {displayEvents.length === 0 ? (
                <div className="text-argus-text-dim text-sm py-4 text-center">
                  {connected
                    ? 'No events yet — waiting for WebSocket messages'
                    : 'WebSocket disconnected'}
                </div>
              ) : (
                <div className="space-y-0">
                  {displayEvents.map((event, index) => (
                    <EventRow key={`${event.sequence}-${index}`} event={event} />
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
