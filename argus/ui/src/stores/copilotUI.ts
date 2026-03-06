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

  // Streaming completion — transitions streaming to final message
  finalizeStreamingMessage: (messageId: string, fullContent: string, toolUse?: ToolUseData[]) => void;

  // Reset conversation state (e.g., when loading a new conversation)
  resetConversation: () => void;
}

export const useCopilotUIStore = create<CopilotUIState>((set) => ({
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
