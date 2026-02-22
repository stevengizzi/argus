/**
 * Reconnecting WebSocket client for real-time event streaming.
 *
 * Automatically reconnects with exponential backoff on disconnection.
 */

import type { WebSocketMessage } from './types';
import { getToken } from './client';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
export type MessageHandler = (message: WebSocketMessage) => void;
export type StatusHandler = (status: WebSocketStatus) => void;

interface WebSocketClientOptions {
  maxReconnectAttempts?: number;
  baseDelay?: number;
  maxDelay?: number;
}

const DEFAULT_OPTIONS: Required<WebSocketClientOptions> = {
  maxReconnectAttempts: 10,
  baseDelay: 1000,
  maxDelay: 30000,
};

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private options: Required<WebSocketClientOptions>;
  private reconnectAttempts = 0;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private messageHandlers: Set<MessageHandler> = new Set();
  private statusHandlers: Set<StatusHandler> = new Set();
  private _status: WebSocketStatus = 'disconnected';
  private intentionalClose = false;

  constructor(url?: string, options: WebSocketClientOptions = {}) {
    // Default to relative WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    this.url = url || `${protocol}//${host}/ws/v1/live`;
    this.options = { ...DEFAULT_OPTIONS, ...options };
  }

  get status(): WebSocketStatus {
    return this._status;
  }

  private setStatus(status: WebSocketStatus): void {
    this._status = status;
    this.statusHandlers.forEach((handler) => handler(status));
  }

  connect(): void {
    const token = getToken();
    if (!token) {
      console.error('WebSocket: No auth token available');
      this.setStatus('error');
      return;
    }

    this.intentionalClose = false;
    this.setStatus('connecting');

    try {
      const wsUrl = `${this.url}?token=${encodeURIComponent(token)}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.setStatus('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.messageHandlers.forEach((handler) => handler(message));
        } catch (error) {
          console.error('WebSocket: Failed to parse message', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log(`WebSocket closed: code=${event.code}, reason=${event.reason}`);
        this.setStatus('disconnected');

        if (!this.intentionalClose) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error', error);
        this.setStatus('error');
      };
    } catch (error) {
      console.error('WebSocket: Failed to connect', error);
      this.setStatus('error');
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.intentionalClose = true;

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.setStatus('disconnected');
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.error('WebSocket: Max reconnection attempts reached');
      this.setStatus('error');
      return;
    }

    // Exponential backoff with jitter
    const delay = Math.min(
      this.options.baseDelay * Math.pow(2, this.reconnectAttempts) +
        Math.random() * 1000,
      this.options.maxDelay
    );

    console.log(
      `WebSocket: Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts + 1})`
    );

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStatusChange(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  send(message: object): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket: Cannot send, not connected');
    }
  }
}

// Singleton instance
let wsClient: WebSocketClient | null = null;

export function getWebSocketClient(): WebSocketClient {
  if (!wsClient) {
    wsClient = new WebSocketClient();
  }
  return wsClient;
}

export function resetWebSocketClient(): void {
  if (wsClient) {
    wsClient.disconnect();
    wsClient = null;
  }
}
