/**
 * Tests for copilotUI store.
 *
 * Sprint 22, Session 4a.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useCopilotUIStore } from '../copilotUI';

describe('copilotUI store', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useCopilotUIStore.setState({
      isOpen: false,
      messages: [],
      conversationId: null,
      isStreaming: false,
      streamingContent: '',
      wsConnected: false,
      aiEnabled: false,
      error: null,
      isLoading: false,
    });
  });

  describe('panel state', () => {
    it('toggles panel open/close', () => {
      const store = useCopilotUIStore.getState();

      expect(store.isOpen).toBe(false);

      store.toggle();
      expect(useCopilotUIStore.getState().isOpen).toBe(true);

      store.toggle();
      expect(useCopilotUIStore.getState().isOpen).toBe(false);
    });
  });

  describe('streaming state transitions', () => {
    it('setIsStreaming transitions to streaming state', () => {
      const store = useCopilotUIStore.getState();

      store.setIsStreaming(true);
      expect(useCopilotUIStore.getState().isStreaming).toBe(true);

      store.setIsStreaming(false);
      expect(useCopilotUIStore.getState().isStreaming).toBe(false);
    });

    it('appendStreamingContent accumulates content', () => {
      const store = useCopilotUIStore.getState();

      store.setStreamingContent('');
      store.appendStreamingContent('Hello');
      expect(useCopilotUIStore.getState().streamingContent).toBe('Hello');

      store.appendStreamingContent(' world');
      expect(useCopilotUIStore.getState().streamingContent).toBe('Hello world');

      store.appendStreamingContent('!');
      expect(useCopilotUIStore.getState().streamingContent).toBe('Hello world!');
    });

    it('finalizeStreamingMessage adds message and clears streaming state', () => {
      const store = useCopilotUIStore.getState();

      // Start streaming
      store.setIsStreaming(true);
      store.setStreamingContent('Test content');

      // Finalize
      store.finalizeStreamingMessage('msg-123', 'Final content');

      const state = useCopilotUIStore.getState();
      expect(state.isStreaming).toBe(false);
      expect(state.streamingContent).toBe('');
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0]).toMatchObject({
        id: 'msg-123',
        role: 'assistant',
        content: 'Final content',
        isComplete: true,
      });
    });
  });

  describe('message management', () => {
    it('addMessage appends to messages array', () => {
      const store = useCopilotUIStore.getState();

      store.addMessage({
        id: '1',
        role: 'user',
        content: 'First message',
        isComplete: true,
        createdAt: new Date().toISOString(),
      });

      expect(useCopilotUIStore.getState().messages).toHaveLength(1);

      store.addMessage({
        id: '2',
        role: 'assistant',
        content: 'Second message',
        isComplete: true,
        createdAt: new Date().toISOString(),
      });

      const messages = useCopilotUIStore.getState().messages;
      expect(messages).toHaveLength(2);
      expect(messages[0].role).toBe('user');
      expect(messages[1].role).toBe('assistant');
    });

    it('setMessages replaces all messages', () => {
      const store = useCopilotUIStore.getState();

      store.addMessage({
        id: '1',
        role: 'user',
        content: 'Old message',
        isComplete: true,
        createdAt: new Date().toISOString(),
      });

      store.setMessages([
        {
          id: '2',
          role: 'assistant',
          content: 'New message',
          isComplete: true,
          createdAt: new Date().toISOString(),
        },
      ]);

      const messages = useCopilotUIStore.getState().messages;
      expect(messages).toHaveLength(1);
      expect(messages[0].id).toBe('2');
    });
  });

  describe('error handling', () => {
    it('setError and clearError work correctly', () => {
      const store = useCopilotUIStore.getState();

      store.setError('Connection failed');
      expect(useCopilotUIStore.getState().error).toBe('Connection failed');

      store.clearError();
      expect(useCopilotUIStore.getState().error).toBeNull();
    });
  });

  describe('resetConversation', () => {
    it('clears conversation state', () => {
      const store = useCopilotUIStore.getState();

      // Set up some state
      store.setMessages([
        {
          id: '1',
          role: 'user',
          content: 'Test',
          isComplete: true,
          createdAt: new Date().toISOString(),
        },
      ]);
      store.setConversationId('conv-123');
      store.setIsStreaming(true);
      store.setStreamingContent('Partial');
      store.setError('Some error');

      // Reset
      store.resetConversation();

      const state = useCopilotUIStore.getState();
      expect(state.messages).toHaveLength(0);
      expect(state.conversationId).toBeNull();
      expect(state.isStreaming).toBe(false);
      expect(state.streamingContent).toBe('');
      expect(state.error).toBeNull();
    });
  });
});
