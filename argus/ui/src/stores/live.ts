/**
 * Live data store using Zustand.
 *
 * Manages WebSocket connection status, real-time price updates,
 * heartbeat tracking, and React Query cache invalidation.
 */

import { create } from 'zustand';
import type { QueryClient } from '@tanstack/react-query';
import { getWebSocketClient, type WebSocketStatus } from '../api/ws';
import type { WebSocketMessage } from '../api/types';

const MAX_RECENT_EVENTS = 50;

// Typed price update from WebSocket
interface PriceUpdate {
  price: number;
  volume: number;
  timestamp: string;
}

// WebSocket event type mapping (from spec)
type WSEventType =
  | 'position.opened'
  | 'position.closed'
  | 'position.updated'
  | 'order.submitted'
  | 'order.filled'
  | 'order.cancelled'
  | 'system.circuit_breaker'
  | 'system.heartbeat'
  | 'scanner.watchlist'
  | 'strategy.signal'
  | 'order.approved'
  | 'order.rejected'
  | 'price.update';

interface LiveState {
  // Connection state
  connected: boolean;
  status: WebSocketStatus;

  // Event tracking
  lastMessage: WebSocketMessage | null;
  recentEvents: WebSocketMessage[];

  // Typed state from WebSocket events
  priceUpdates: Record<string, PriceUpdate>;
  lastHeartbeat: string | null;

  // Actions
  connect: () => void;
  disconnect: () => void;
  clearEvents: () => void;
}

// QueryClient reference for cache invalidation
let queryClient: QueryClient | null = null;

/**
 * Set the QueryClient instance for cache invalidation.
 * Call this once in main.tsx after creating the QueryClient.
 */
export function setQueryClient(client: QueryClient): void {
  queryClient = client;
}

/**
 * Invalidate React Query cache based on WebSocket event type.
 */
function invalidateCacheForEvent(eventType: string): void {
  if (!queryClient) return;

  // Handle orchestrator.* events (regime changes, allocation updates, etc.)
  if (eventType.startsWith('orchestrator.')) {
    queryClient.invalidateQueries({ queryKey: ['orchestrator-status'] });
    queryClient.invalidateQueries({ queryKey: ['orchestrator-decisions'] });
    return;
  }

  switch (eventType as WSEventType) {
    case 'position.opened':
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['account'] });
      break;

    case 'position.closed':
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['account'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      queryClient.invalidateQueries({ queryKey: ['performance', 'today'] });
      break;

    case 'order.filled':
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['account'] });
      break;

    case 'system.circuit_breaker':
      queryClient.invalidateQueries({ queryKey: ['health'] });
      break;

    default:
      // No cache invalidation needed for other event types
      break;
  }
}

/**
 * Extract price update data from a price.update WebSocket message.
 */
function extractPriceUpdate(data: unknown): { symbol: string; update: PriceUpdate } | null {
  if (
    typeof data === 'object' &&
    data !== null &&
    'symbol' in data &&
    'price' in data
  ) {
    const d = data as Record<string, unknown>;
    return {
      symbol: String(d.symbol),
      update: {
        price: Number(d.price),
        volume: Number(d.volume ?? 0),
        timestamp: String(d.timestamp ?? new Date().toISOString()),
      },
    };
  }
  return null;
}

export const useLiveStore = create<LiveState>((set, get) => ({
  // Connection state
  connected: false,
  status: 'disconnected',

  // Event tracking
  lastMessage: null,
  recentEvents: [],

  // Typed state
  priceUpdates: {},
  lastHeartbeat: null,

  connect: () => {
    const client = getWebSocketClient();

    // Set up status handler
    client.onStatusChange((status) => {
      set({
        status,
        connected: status === 'connected',
      });
    });

    // Set up message handler
    client.onMessage((message) => {
      const { recentEvents, priceUpdates } = get();
      const newEvents = [message, ...recentEvents].slice(0, MAX_RECENT_EVENTS);

      // Build updated state
      const updates: Partial<LiveState> = {
        lastMessage: message,
        recentEvents: newEvents,
      };

      // Handle typed events
      const eventType = message.type as WSEventType;

      if (eventType === 'system.heartbeat') {
        updates.lastHeartbeat = message.timestamp;
      }

      if (eventType === 'price.update') {
        const priceData = extractPriceUpdate(message.data);
        if (priceData) {
          updates.priceUpdates = {
            ...priceUpdates,
            [priceData.symbol]: priceData.update,
          };
        }
      }

      // Apply state updates
      set(updates);

      // Invalidate React Query cache based on event type
      invalidateCacheForEvent(eventType);
    });

    // Connect
    client.connect();
  },

  disconnect: () => {
    const client = getWebSocketClient();
    client.disconnect();
    set({
      connected: false,
      status: 'disconnected',
    });
  },

  clearEvents: () => {
    set({
      recentEvents: [],
      lastMessage: null,
      priceUpdates: {},
    });
  },
}));
