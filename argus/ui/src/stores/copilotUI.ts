/**
 * AI Copilot panel UI state store using Zustand.
 *
 * Manages:
 * - Panel open/close state
 * - Chat messages and conversation state
 * - WebSocket connection and streaming state
 * - Session-level only — does not persist to localStorage.
 *
 * Sprint 21d — Copilot shell. Sprint 22 — Live chat integration.
 */

import { create } from 'zustand';

// Message types
export interface ToolUseData {
  toolName: string;
  toolInput: Record<string, unknown>;
  proposalId: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolUse?: ToolUseData[];
  isComplete: boolean;
  createdAt: string;
}

// Context provider function type
export type ContextProvider = () => Record<string, unknown>;

interface CopilotUIState {
  // Panel state
  isOpen: boolean;

  // Chat state
  messages: ChatMessage[];
  conversationId: string | null;
  isStreaming: boolean;
  streamingContent: string;
  wsConnected: boolean;
  aiEnabled: boolean;
  error: string | null;
  isLoading: boolean;

  // Page context state
  currentPage: string | null;
  contextProvider: ContextProvider | null;

  // Reconnection state
  isReconnecting: boolean;
  reconnectAttempt: number;

  // Panel actions
  toggle: () => void;
  open: () => void;
  close: () => void;

  // Chat actions
  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  setConversationId: (id: string | null) => void;
  setIsStreaming: (streaming: boolean) => void;
  setStreamingContent: (content: string) => void;
  appendStreamingContent: (content: string) => void;
  setWsConnected: (connected: boolean) => void;
  setAiEnabled: (enabled: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  setIsLoading: (loading: boolean) => void;

  // Context provider actions
  registerContextProvider: (page: string, provider: ContextProvider) => void;
  unregisterContextProvider: (page: string) => void;
  getPageContext: () => { page: string; context: Record<string, unknown> };

  // Reconnection actions
  setIsReconnecting: (reconnecting: boolean) => void;
  setReconnectAttempt: (attempt: number) => void;

  // Streaming completion — transitions streaming to final message
  finalizeStreamingMessage: (messageId: string, fullContent: string, toolUse?: ToolUseData[]) => void;

  // Reset conversation state (e.g., when loading a new conversation)
  resetConversation: () => void;
}

export const useCopilotUIStore = create<CopilotUIState>((set, get) => ({
  // Panel state
  isOpen: false,

  // Chat state
  messages: [],
  conversationId: null,
  isStreaming: false,
  streamingContent: '',
  wsConnected: false,
  aiEnabled: false,
  error: null,
  isLoading: false,

  // Page context state
  currentPage: null,
  contextProvider: null,

  // Reconnection state
  isReconnecting: false,
  reconnectAttempt: 0,

  // Panel actions
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),

  // Chat actions
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  setConversationId: (conversationId) => set({ conversationId }),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setStreamingContent: (streamingContent) => set({ streamingContent }),
  appendStreamingContent: (content) => set((state) => ({
    streamingContent: state.streamingContent + content
  })),
  setWsConnected: (wsConnected) => set({ wsConnected }),
  setAiEnabled: (aiEnabled) => set({ aiEnabled }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),
  setIsLoading: (isLoading) => set({ isLoading }),

  // Context provider actions
  registerContextProvider: (page, provider) => set({ currentPage: page, contextProvider: provider }),
  unregisterContextProvider: (page) => set((state) => {
    // Only unregister if this page is the current provider
    if (state.currentPage === page) {
      return { currentPage: null, contextProvider: null };
    }
    return {};
  }),
  getPageContext: () => {
    const state = get();
    const page = state.currentPage || 'Unknown';
    const context = state.contextProvider ? state.contextProvider() : {};
    return { page, context };
  },

  // Reconnection actions
  setIsReconnecting: (isReconnecting) => set({ isReconnecting }),
  setReconnectAttempt: (reconnectAttempt) => set({ reconnectAttempt }),

  // Streaming completion
  finalizeStreamingMessage: (messageId, fullContent, toolUse) => set((state) => {
    const newMessage: ChatMessage = {
      id: messageId,
      role: 'assistant',
      content: fullContent,
      toolUse,
      isComplete: true,
      createdAt: new Date().toISOString(),
    };
    return {
      messages: [...state.messages, newMessage],
      isStreaming: false,
      streamingContent: '',
    };
  }),

  // Reset conversation
  resetConversation: () => set({
    messages: [],
    conversationId: null,
    isStreaming: false,
    streamingContent: '',
    error: null,
  }),
}));
