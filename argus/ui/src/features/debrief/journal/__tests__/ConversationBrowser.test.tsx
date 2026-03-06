/**
 * Tests for ConversationBrowser component.
 *
 * Sprint 22 Session 6.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConversationBrowser } from '../ConversationBrowser';
import type { ConversationsListResponse, ConversationDetailResponse } from '../../../../api/types';

// Mock hooks
const mockUseConversations = vi.fn();
const mockUseConversation = vi.fn();
const mockUseCopilotUIStore = vi.fn();

vi.mock('../../../../hooks', () => ({
  useConversations: (filters?: unknown) => mockUseConversations(filters),
  useConversation: (id: string | null) => mockUseConversation(id),
}));

vi.mock('../../../../stores/copilotUI', () => ({
  useCopilotUIStore: (selector: (state: unknown) => unknown) => mockUseCopilotUIStore(selector),
}));

const mockConversationsData: ConversationsListResponse = {
  conversations: [
    {
      id: 'conv-1',
      date: '2026-03-06',
      tag: 'session',
      title: 'Morning trading discussion',
      message_count: 5,
      created_at: '2026-03-06T09:30:00Z',
      updated_at: '2026-03-06T10:00:00Z',
    },
    {
      id: 'conv-2',
      date: '2026-03-05',
      tag: 'research',
      title: 'Strategy performance analysis',
      message_count: 8,
      created_at: '2026-03-05T14:00:00Z',
      updated_at: '2026-03-05T15:00:00Z',
    },
  ],
  total: 2,
};

const mockConversationDetail: ConversationDetailResponse = {
  conversation: {
    id: 'conv-1',
    date: '2026-03-06',
    tag: 'session',
    title: 'Morning trading discussion',
    message_count: 2,
    created_at: '2026-03-06T09:30:00Z',
    updated_at: '2026-03-06T10:00:00Z',
  },
  messages: [
    {
      id: 'msg-1',
      conversation_id: 'conv-1',
      role: 'user',
      content: 'What is the market outlook today?',
      tool_use_data: null,
      page_context: null,
      is_complete: true,
      created_at: '2026-03-06T09:30:00Z',
    },
    {
      id: 'msg-2',
      conversation_id: 'conv-1',
      role: 'assistant',
      content: 'Based on pre-market indicators, the market looks bullish.',
      tool_use_data: null,
      page_context: null,
      is_complete: true,
      created_at: '2026-03-06T09:30:30Z',
    },
  ],
};

describe('ConversationBrowser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCopilotUIStore.mockReturnValue(vi.fn());
  });

  it('renders Learning Journal header', () => {
    mockUseConversations.mockReturnValue({
      data: mockConversationsData,
      isLoading: false,
      error: null,
    });
    mockUseConversation.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    render(<ConversationBrowser />);

    expect(screen.getByText('Learning Journal')).toBeInTheDocument();
  });

  it('renders conversation list items', () => {
    mockUseConversations.mockReturnValue({
      data: mockConversationsData,
      isLoading: false,
      error: null,
    });
    mockUseConversation.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    render(<ConversationBrowser />);

    expect(screen.getByText('Morning trading discussion')).toBeInTheDocument();
    expect(screen.getByText('Strategy performance analysis')).toBeInTheDocument();
    expect(screen.getByText('5 messages')).toBeInTheDocument();
    expect(screen.getByText('8 messages')).toBeInTheDocument();
  });

  it('renders tag badges with correct labels', () => {
    mockUseConversations.mockReturnValue({
      data: mockConversationsData,
      isLoading: false,
      error: null,
    });
    mockUseConversation.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    render(<ConversationBrowser />);

    expect(screen.getByText('session')).toBeInTheDocument();
    expect(screen.getByText('research')).toBeInTheDocument();
  });

  it('shows empty state when no conversations exist', () => {
    mockUseConversations.mockReturnValue({
      data: { conversations: [], total: 0 },
      isLoading: false,
      error: null,
    });
    mockUseConversation.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    render(<ConversationBrowser />);

    expect(screen.getByText('No conversations yet')).toBeInTheDocument();
    expect(screen.getByText(/Start chatting with the Copilot/)).toBeInTheDocument();
  });

  it('shows Open Copilot button in empty state', () => {
    mockUseConversations.mockReturnValue({
      data: { conversations: [], total: 0 },
      isLoading: false,
      error: null,
    });
    mockUseConversation.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    render(<ConversationBrowser />);

    expect(screen.getByText('Open Copilot')).toBeInTheDocument();
  });

  it('renders date filter presets', () => {
    mockUseConversations.mockReturnValue({
      data: mockConversationsData,
      isLoading: false,
      error: null,
    });
    mockUseConversation.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    render(<ConversationBrowser />);

    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('This Week')).toBeInTheDocument();
    expect(screen.getByText('This Month')).toBeInTheDocument();
    expect(screen.getByText('All')).toBeInTheDocument();
  });

  it('renders tag filter button', () => {
    mockUseConversations.mockReturnValue({
      data: mockConversationsData,
      isLoading: false,
      error: null,
    });
    mockUseConversation.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    render(<ConversationBrowser />);

    expect(screen.getByText('Tags')).toBeInTheDocument();
  });

  it('opens conversation detail view when clicking a conversation', async () => {
    mockUseConversations.mockReturnValue({
      data: mockConversationsData,
      isLoading: false,
      error: null,
    });
    mockUseConversation.mockReturnValue({
      data: mockConversationDetail,
      isLoading: false,
      error: null,
    });

    render(<ConversationBrowser />);

    // Click on the first conversation
    const conversationButton = screen.getByText('Morning trading discussion');
    fireEvent.click(conversationButton);

    // Should show messages
    await waitFor(() => {
      expect(screen.getByText('What is the market outlook today?')).toBeInTheDocument();
    });
  });

  it('shows loading skeleton when fetching conversations', () => {
    mockUseConversations.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    });
    mockUseConversation.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    const { container } = render(<ConversationBrowser />);

    // Check for skeleton animation
    const pulsingElements = container.querySelectorAll('.animate-pulse');
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  it('shows error state when fetch fails', () => {
    mockUseConversations.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('Failed to fetch'),
    });
    mockUseConversation.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    render(<ConversationBrowser />);

    expect(screen.getByText('Failed to load conversations')).toBeInTheDocument();
  });
});
