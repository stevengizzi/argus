/**
 * Tests for ChatMessage component.
 *
 * Sprint 22, Session 4a. Updated Session 5 for ActionCard integration.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatMessage } from '../ChatMessage';
import type { ChatMessage as ChatMessageType } from '../../../stores/copilotUI';

// Mock clipboard API
const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};
Object.assign(navigator, { clipboard: mockClipboard });

// Mock the copilot store
const mockProposals: Record<string, unknown> = {};
vi.mock('../../../stores/copilotUI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../stores/copilotUI')>();
  return {
    ...actual,
    useCopilotUIStore: vi.fn((selector) => {
      const state = {
        proposals: mockProposals,
        notificationsEnabled: false,
        setProposal: vi.fn((p: { id: string }) => { mockProposals[p.id] = p; }),
        updateProposal: vi.fn(),
      };
      return typeof selector === 'function' ? selector(state) : state;
    }),
  };
});

// Mock the notifications utility
vi.mock('../../../utils/notifications', () => ({
  playProposalNotification: vi.fn(),
  playExpiryWarning: vi.fn(),
  initializeAudioContext: vi.fn(),
}));

// Mock the API
vi.mock('../api', () => ({
  approveProposal: vi.fn().mockResolvedValue({ proposal: { status: 'approved' } }),
  rejectProposal: vi.fn().mockResolvedValue({ proposal: { status: 'rejected' } }),
}));

describe('ChatMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders user message with right-aligned bubble', () => {
    const message: ChatMessageType = {
      id: '1',
      role: 'user',
      content: 'Hello, how are you?',
      isComplete: true,
      createdAt: new Date().toISOString(),
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText('Hello, how are you?')).toBeInTheDocument();
    // User messages should be right-aligned (flex-col items-end)
    const container = screen.getByText('Hello, how are you?').closest('div[class*="items-end"]');
    expect(container).toBeInTheDocument();
  });

  it('renders assistant message with markdown support', () => {
    const message: ChatMessageType = {
      id: '2',
      role: 'assistant',
      content: 'Here is some **bold** and *italic* text.',
      isComplete: true,
      createdAt: new Date().toISOString(),
    };

    render(<ChatMessage message={message} />);

    // The bold text should be rendered
    expect(screen.getByText(/bold/)).toBeInTheDocument();
    expect(screen.getByText(/italic/)).toBeInTheDocument();
  });

  it('renders code blocks with proper styling', () => {
    const message: ChatMessageType = {
      id: '3',
      role: 'assistant',
      content: 'Here is some code:\n\n```python\nprint("hello")\n```',
      isComplete: true,
      createdAt: new Date().toISOString(),
    };

    render(<ChatMessage message={message} />);

    // Code block should be rendered
    expect(screen.getByText('print("hello")')).toBeInTheDocument();
  });

  it('shows copy button on hover for assistant messages', async () => {
    const message: ChatMessageType = {
      id: '4',
      role: 'assistant',
      content: 'Copy me!',
      isComplete: true,
      createdAt: new Date().toISOString(),
    };

    render(<ChatMessage message={message} />);

    // Find the message container and hover
    const messageContainer = screen.getByText('Copy me!').closest('div[class*="group"]');
    expect(messageContainer).toBeInTheDocument();

    // Simulate hover
    fireEvent.mouseEnter(messageContainer!);

    // Copy button should appear
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /copy/i })).toBeInTheDocument();
    });

    // Click copy button
    fireEvent.click(screen.getByRole('button', { name: /copy/i }));

    // Clipboard should be called
    expect(mockClipboard.writeText).toHaveBeenCalledWith('Copy me!');
  });

  it('renders ActionCard when toolUse data present with proposalId', () => {
    // Pre-populate the mock proposals store
    const proposalId = 'prop-123';
    mockProposals[proposalId] = {
      id: proposalId,
      toolName: 'propose_allocation_change',
      toolInput: { strategy_id: 'orb', new_allocation_pct: 25, reason: 'Testing' },
      status: 'pending',
      expiresAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
    };

    const message: ChatMessageType = {
      id: '5',
      role: 'assistant',
      content: 'I will help you with that.',
      toolUse: [
        {
          toolName: 'propose_allocation_change',
          toolInput: { strategy_id: 'orb', new_allocation_pct: 25, reason: 'Testing' },
          proposalId: proposalId,
        },
      ],
      isComplete: true,
      createdAt: new Date().toISOString(),
    };

    render(<ChatMessage message={message} />);

    // ActionCard should be rendered with Allocation Change label
    expect(screen.getByText('Allocation Change')).toBeInTheDocument();

    // Clean up
    delete mockProposals[proposalId];
  });

  it('displays relative timestamp', () => {
    const message: ChatMessageType = {
      id: '6',
      role: 'user',
      content: 'Test message',
      isComplete: true,
      createdAt: new Date().toISOString(), // Just now
    };

    render(<ChatMessage message={message} />);

    // Should show "just now" for recent messages
    expect(screen.getByText('just now')).toBeInTheDocument();
  });
});
