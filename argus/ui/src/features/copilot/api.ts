/**
 * AI Copilot API client and WebSocket manager.
 *
 * Provides REST endpoints for conversation history and AI status,
 * plus WebSocket streaming for real-time chat.
 *
 * Sprint 22, Session 4a.
 */

import { getToken } from '../../api/client';
import { useCopilotUIStore, type ChatMessage, type ToolUseData } from '../../stores/copilotUI';

const API_BASE = '/api/v1';

// --- REST API Types ---

export interface ConversationSummary {
  id: string;
  date: string;
  tag: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  tool_use_data: ToolUseData[] | null;
  page_context: Record<string, unknown> | null;
  is_complete: boolean;
  created_at: string;
}

export interface ConversationsListResponse {
  conversations: ConversationSummary[];
  total: number;
}

export interface ConversationDetailResponse {
  conversation: ConversationSummary;
  messages: MessageResponse[];
}

export interface AIStatusResponse {
  enabled: boolean;
  model: string | null;
  usage: {
    today: Record<string, unknown>;
    this_month: Record<string, unknown>;
    per_day_average: number;
  } | null;
}

export interface ChatRequest {
  conversation_id: string | null;
  message: string;
  page: string;
  page_context: Record<string, unknown>;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  content: string;
  tool_use: Array<{
    id: string;
    name: string;
    input: Record<string, unknown>;
    proposal_id: string | null;
  }> | null;
}

// --- REST API Methods ---

async function fetchWithAuth<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  headers.set('Content-Type', 'application/json');

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(errorBody.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function fetchAIStatus(): Promise<AIStatusResponse> {
  return fetchWithAuth<AIStatusResponse>('/ai/status');
}

export async function fetchConversations(params?: {
  date_from?: string;
  date_to?: string;
  tag?: string;
  limit?: number;
  offset?: number;
}): Promise<ConversationsListResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return fetchWithAuth<ConversationsListResponse>(`/ai/conversations${query ? `?${query}` : ''}`);
}

export async function fetchConversation(
  conversationId: string,
  params?: { limit?: number; offset?: number }
): Promise<ConversationDetailResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return fetchWithAuth<ConversationDetailResponse>(
    `/ai/conversations/${conversationId}${query ? `?${query}` : ''}`
  );
}

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  return fetchWithAuth<ChatResponse>('/ai/chat', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// --- WebSocket Manager ---

type WebSocketState = 'disconnected' | 'connecting' | 'authenticating' | 'connected' | 'error';

interface ChatWebSocketManager {
  connect: () => void;
  disconnect: () => void;
  sendMessage: (content: string, page: string, pageContext: Record<string, unknown>) => void;
  cancelStream: () => void;
  getState: () => WebSocketState;
}

class CopilotWebSocketManager implements ChatWebSocketManager {
  private ws: WebSocket | null = null;
  private state: WebSocketState = 'disconnected';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;
  private pendingMessageId: string | null = null;

  connect(): void {
    const token = getToken();
    if (!token) {
      console.error('CopilotWS: No auth token available');
      this.state = 'error';
      useCopilotUIStore.getState().setWsConnected(false);
      useCopilotUIStore.getState().setError('Authentication required');
      return;
    }

    this.intentionalClose = false;
    this.state = 'connecting';

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/v1/ai/chat`;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        if (import.meta.env.DEV) console.log('CopilotWS: Connected, sending auth');
        this.state = 'authenticating';
        // Send auth message
        this.ws?.send(JSON.stringify({
          type: 'auth',
          token: token,
        }));
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event);
      };

      this.ws.onclose = (event) => {
        if (import.meta.env.DEV) console.log(`CopilotWS: Closed code=${event.code}`);
        this.state = 'disconnected';
        useCopilotUIStore.getState().setWsConnected(false);

        if (!this.intentionalClose) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('CopilotWS: Error', error);
        this.state = 'error';
        useCopilotUIStore.getState().setWsConnected(false);
      };
    } catch (error) {
      console.error('CopilotWS: Failed to connect', error);
      this.state = 'error';
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

    this.state = 'disconnected';
    this.reconnectAttempts = 0;
    useCopilotUIStore.getState().setWsConnected(false);
  }

  private scheduleReconnect(): void {
    const store = useCopilotUIStore.getState();

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('CopilotWS: Max reconnection attempts reached');
      this.state = 'error';
      store.setIsReconnecting(false);
      store.setReconnectAttempt(0);
      store.setError('Connection failed. Please refresh.');
      return;
    }

    // Show reconnecting banner
    store.setIsReconnecting(true);
    store.setReconnectAttempt(this.reconnectAttempts + 1);

    // Exponential backoff: 1s, 2s, 4s
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 4000);

    if (import.meta.env.DEV) {
      console.log(`CopilotWS: Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);
    }

    this.reconnectTimeout = setTimeout(async () => {
      this.reconnectAttempts++;

      // Re-fetch current conversation from REST to sync state
      await this.syncConversationFromRest();

      // Attempt WebSocket reconnect
      this.connect();
    }, delay);
  }

  private async syncConversationFromRest(): Promise<void> {
    const store = useCopilotUIStore.getState();
    const conversationId = store.conversationId;

    if (!conversationId) {
      return;
    }

    try {
      if (import.meta.env.DEV) {
        console.log('CopilotWS: Re-fetching conversation from REST');
      }

      const response = await fetchConversation(conversationId);

      // Convert API messages to store format
      const messages: ChatMessage[] = response.messages.map((msg) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        toolUse: msg.tool_use_data || undefined,
        isComplete: msg.is_complete,
        createdAt: msg.created_at,
      }));

      // Replace any partial/streaming messages with persisted versions
      store.setMessages(messages);
      store.setIsStreaming(false);
      store.setStreamingContent('');
      this.pendingMessageId = null;

      if (import.meta.env.DEV) {
        console.log(`CopilotWS: Synced ${messages.length} messages from REST`);
      }
    } catch (error) {
      console.error('CopilotWS: Failed to sync conversation', error);
      // Don't block reconnection attempt — just log the error
    }
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      const store = useCopilotUIStore.getState();

      switch (data.type) {
        case 'auth_success':
          if (import.meta.env.DEV) console.log('CopilotWS: Authenticated');
          this.state = 'connected';
          this.reconnectAttempts = 0;
          store.setWsConnected(true);
          // Clear reconnecting state on successful connection
          store.setIsReconnecting(false);
          store.setReconnectAttempt(0);
          break;

        case 'stream_start':
          this.pendingMessageId = data.message_id;
          // If conversation_id is provided and different, update store
          if (data.conversation_id && data.conversation_id !== store.conversationId) {
            store.setConversationId(data.conversation_id);
          }
          store.setIsStreaming(true);
          store.setStreamingContent('');
          break;

        case 'token':
          store.appendStreamingContent(data.content);
          break;

        case 'tool_use': {
          // Tool use arrives during stream — we'll collect them
          // For now, just log. Session 5 builds ActionCard.
          const toolUseData: ToolUseData = {
            toolName: data.tool_name,
            toolInput: data.tool_input,
            proposalId: data.proposal_id,
          };
          if (import.meta.env.DEV) {
            console.log('CopilotWS: Tool use', toolUseData);
          }
          // We'll store tool_use in the finalized message
          break;
        }

        case 'stream_end': {
          const messageId = this.pendingMessageId || crypto.randomUUID();
          this.pendingMessageId = null;
          store.finalizeStreamingMessage(messageId, data.full_content);
          break;
        }

        case 'error':
          store.setError(data.message || 'An error occurred');
          store.setIsStreaming(false);
          this.pendingMessageId = null;
          break;

        default:
          if (import.meta.env.DEV) {
            console.log('CopilotWS: Unknown message type', data.type);
          }
      }
    } catch (error) {
      console.error('CopilotWS: Failed to parse message', error);
    }
  }

  sendMessage(content: string, page: string, pageContext: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('CopilotWS: Cannot send, not connected');
      useCopilotUIStore.getState().setError('Not connected to AI service');
      return;
    }

    const store = useCopilotUIStore.getState();

    // Add user message to store immediately for optimistic UI
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      isComplete: true,
      createdAt: new Date().toISOString(),
    };
    store.addMessage(userMessage);

    // Send via WebSocket
    this.ws.send(JSON.stringify({
      type: 'message',
      conversation_id: store.conversationId,
      content,
      page,
      page_context: pageContext,
    }));
  }

  cancelStream(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    this.ws.send(JSON.stringify({ type: 'cancel' }));
    useCopilotUIStore.getState().setIsStreaming(false);
  }

  getState(): WebSocketState {
    return this.state;
  }
}

// Singleton instance
let wsManager: CopilotWebSocketManager | null = null;

export function getCopilotWebSocket(): ChatWebSocketManager {
  if (!wsManager) {
    wsManager = new CopilotWebSocketManager();
  }
  return wsManager;
}

export function resetCopilotWebSocket(): void {
  if (wsManager) {
    wsManager.disconnect();
    wsManager = null;
  }
}

// --- Conversation Loading Helper ---

export async function loadConversation(conversationId: string): Promise<void> {
  const store = useCopilotUIStore.getState();
  store.setIsLoading(true);
  store.setError(null);

  try {
    const response = await fetchConversation(conversationId);

    // Convert API messages to store format
    const messages: ChatMessage[] = response.messages.map((msg) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      toolUse: msg.tool_use_data || undefined,
      isComplete: msg.is_complete,
      createdAt: msg.created_at,
    }));

    store.setMessages(messages);
    store.setConversationId(conversationId);
  } catch (error) {
    store.setError(error instanceof Error ? error.message : 'Failed to load conversation');
  } finally {
    store.setIsLoading(false);
  }
}

export async function loadTodayConversation(): Promise<void> {
  const store = useCopilotUIStore.getState();
  store.setIsLoading(true);
  store.setError(null);

  try {
    // Get today's date in YYYY-MM-DD format
    const today = new Date().toISOString().split('T')[0];

    // Fetch conversations for today
    const response = await fetchConversations({
      date_from: today,
      date_to: today,
      limit: 1,
    });

    if (response.conversations.length > 0) {
      // Load the most recent conversation
      await loadConversation(response.conversations[0].id);
    } else {
      // No conversation for today — start fresh
      store.setMessages([]);
      store.setConversationId(null);
    }
  } catch (error) {
    // Don't show error for no conversations — just start fresh
    store.setMessages([]);
    store.setConversationId(null);
  } finally {
    store.setIsLoading(false);
  }
}

export async function checkAIStatus(): Promise<boolean> {
  const store = useCopilotUIStore.getState();

  try {
    const status = await fetchAIStatus();
    store.setAiEnabled(status.enabled);
    return status.enabled;
  } catch (error) {
    // If we can't reach the status endpoint, assume disabled
    store.setAiEnabled(false);
    return false;
  }
}
