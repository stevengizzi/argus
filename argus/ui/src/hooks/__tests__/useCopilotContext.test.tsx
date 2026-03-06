/**
 * Tests for useCopilotContext hook.
 *
 * Sprint 22, Session 4b.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useCopilotContext } from '../useCopilotContext';
import { useCopilotUIStore } from '../../stores/copilotUI';

describe('useCopilotContext', () => {
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
      currentPage: null,
      contextProvider: null,
      isReconnecting: false,
      reconnectAttempt: 0,
    });
  });

  it('registers context provider on mount', () => {
    const contextFn = () => ({ equity: 10000 });

    renderHook(() => useCopilotContext('Dashboard', contextFn));

    const state = useCopilotUIStore.getState();
    expect(state.currentPage).toBe('Dashboard');
    expect(state.contextProvider).toBeDefined();
  });

  it('unregisters context provider on unmount', () => {
    const contextFn = () => ({ equity: 10000 });

    const { unmount } = renderHook(() => useCopilotContext('Dashboard', contextFn));

    expect(useCopilotUIStore.getState().currentPage).toBe('Dashboard');

    unmount();

    expect(useCopilotUIStore.getState().currentPage).toBeNull();
    expect(useCopilotUIStore.getState().contextProvider).toBeNull();
  });

  it('returns page name from hook', () => {
    const contextFn = () => ({ equity: 10000 });

    const { result } = renderHook(() => useCopilotContext('Dashboard', contextFn));

    expect(result.current.page).toBe('Dashboard');
  });

  it('registered provider returns current context data', () => {
    let equity = 10000;
    const contextFn = () => ({ equity });

    renderHook(() => useCopilotContext('Dashboard', contextFn));

    // Call getPageContext to evaluate the provider
    const result1 = useCopilotUIStore.getState().getPageContext();
    expect(result1.context).toEqual({ equity: 10000 });

    // Update the value
    equity = 15000;

    // Provider should return updated value
    const result2 = useCopilotUIStore.getState().getPageContext();
    expect(result2.context).toEqual({ equity: 15000 });
  });

  it('re-registers when page name changes', () => {
    const contextFn = () => ({ data: 'test' });

    const { rerender } = renderHook(
      ({ page }) => useCopilotContext(page, contextFn),
      { initialProps: { page: 'Dashboard' } }
    );

    expect(useCopilotUIStore.getState().currentPage).toBe('Dashboard');

    rerender({ page: 'Trades' });

    expect(useCopilotUIStore.getState().currentPage).toBe('Trades');
  });

  it('does not unregister when different page unmounts', () => {
    const contextFn1 = () => ({ page: 'Dashboard' });
    const contextFn2 = () => ({ page: 'Trades' });

    // Mount Dashboard first
    const { unmount: unmount1 } = renderHook(() => useCopilotContext('Dashboard', contextFn1));

    // Mount Trades (overwrites Dashboard)
    renderHook(() => useCopilotContext('Trades', contextFn2));

    expect(useCopilotUIStore.getState().currentPage).toBe('Trades');

    // Unmount Dashboard — should NOT affect Trades
    unmount1();

    expect(useCopilotUIStore.getState().currentPage).toBe('Trades');
    expect(useCopilotUIStore.getState().contextProvider).toBeDefined();
  });
});
