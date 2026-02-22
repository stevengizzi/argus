/**
 * Live data store using Zustand.
 *
 * Manages WebSocket connection status and recent events.
 */

import { create } from 'zustand';
import { getWebSocketClient, type WebSocketStatus } from '../api/ws';
import type { WebSocketMessage } from '../api/types';

const MAX_RECENT_EVENTS = 50;

interface LiveState {
  connected: boolean;
  status: WebSocketStatus;
  lastMessage: WebSocketMessage | null;
  recentEvents: WebSocketMessage[];

  // Actions
  connect: () => void;
  disconnect: () => void;
  clearEvents: () => void;
}

export const useLiveStore = create<LiveState>((set, get) => ({
  connected: false,
  status: 'disconnected',
  lastMessage: null,
  recentEvents: [],

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
      const { recentEvents } = get();
      const newEvents = [message, ...recentEvents].slice(0, MAX_RECENT_EVENTS);
      set({
        lastMessage: message,
        recentEvents: newEvents,
      });
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
    set({ recentEvents: [], lastMessage: null });
  },
}));
