/**
 * Tests for ConversationHistory component.
 *
 * Sprint 22, Session 4b.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConversationHistory } from '../ConversationHistory';
import { useCopilotUIStore } from '../../../stores/copilotUI';

// Mock the api module
vi.mock('../api', () => ({
  fetchConversations: vi.fn(),
  loadConversation: vi.fn(),
}));

import { fetchConversations, loadConversation } from '../api';

describe('ConversationHistory', () => {
  beforeEach(() => {
    // Reset store
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

    // Reset mocks
    vi.clearAllMocks();
  });

  it('renders toggle button', () => {
    render(<ConversationHistory />);

    expect(screen.getByRole('button', { name: /previous conversations/i })).toBeInTheDocument();
    expect(screen.getByText('Previous')).toBeInTheDocument();
  });

  it('fetches conversations when dropdown opens', async () => {
    const mockConversations = [
      {
        id: 'conv-1',
        date: new Date().toISOString().split('T')[0],
        tag: 'daily',
        title: 'Test conversation',
        message_count: 5,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    (fetchConversations as ReturnType<typeof vi.fn>).mockResolvedValue({
      conversations: mockConversations,
      total: 1,
    });

    render(<ConversationHistory />);

    // Click to open dropdown
    fireEvent.click(screen.getByRole('button', { name: /previous conversations/i }));

    await waitFor(() => {
      expect(fetchConversations).toHaveBeenCalledWith({
        limit: 20,
        offset: 0,
      });
    });

    // Should show the conversation
    await waitFor(() => {
      expect(screen.getByText('Test conversation')).toBeInTheDocument();
    });
  });

  it('shows empty state when no conversations', async () => {
    (fetchConversations as ReturnType<typeof vi.fn>).mockResolvedValue({
      conversations: [],
      total: 0,
    });

    render(<ConversationHistory />);

    fireEvent.click(screen.getByRole('button', { name: /previous conversations/i }));

    await waitFor(() => {
      expect(screen.getByText('No previous conversations')).toBeInTheDocument();
    });
  });

  it('shows loading state while fetching', async () => {
    // Create a promise that doesn't resolve immediately
    let resolvePromise: () => void;
    const pendingPromise = new Promise<void>((resolve) => {
      resolvePromise = resolve;
    });

    (fetchConversations as ReturnType<typeof vi.fn>).mockReturnValue(
      pendingPromise.then(() => ({ conversations: [], total: 0 }))
    );

    render(<ConversationHistory />);

    fireEvent.click(screen.getByRole('button', { name: /previous conversations/i }));

    // Should show loading indicator
    expect(screen.getByRole('button', { name: /previous conversations/i })).toHaveAttribute(
      'aria-expanded',
      'true'
    );

    // Clean up
    resolvePromise!();
    await pendingPromise;
  });

  it('highlights current conversation', async () => {
    const currentId = 'conv-1';
    useCopilotUIStore.setState({ conversationId: currentId });

    const mockConversations = [
      {
        id: currentId,
        date: new Date().toISOString().split('T')[0],
        tag: 'daily',
        title: 'Current conversation',
        message_count: 5,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    (fetchConversations as ReturnType<typeof vi.fn>).mockResolvedValue({
      conversations: mockConversations,
      total: 1,
    });

    render(<ConversationHistory />);

    fireEvent.click(screen.getByRole('button', { name: /previous conversations/i }));

    await waitFor(() => {
      const convButton = screen.getByRole('button', { name: /current conversation/i });
      expect(convButton).toHaveClass('bg-argus-accent/10');
    });
  });

  it('loads conversation when clicked', async () => {
    const mockConversations = [
      {
        id: 'conv-2',
        date: new Date().toISOString().split('T')[0],
        tag: 'daily',
        title: 'Another conversation',
        message_count: 3,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    (fetchConversations as ReturnType<typeof vi.fn>).mockResolvedValue({
      conversations: mockConversations,
      total: 1,
    });
    (loadConversation as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);

    render(<ConversationHistory />);

    fireEvent.click(screen.getByRole('button', { name: /previous conversations/i }));

    await waitFor(() => {
      expect(screen.getByText('Another conversation')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /another conversation/i }));

    await waitFor(() => {
      expect(loadConversation).toHaveBeenCalledWith('conv-2');
    });
  });
});
