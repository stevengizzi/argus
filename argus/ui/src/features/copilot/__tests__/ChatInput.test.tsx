/**
 * Tests for ChatInput component.
 *
 * Sprint 22, Session 4a.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInput } from '../ChatInput';
import { useCopilotUIStore } from '../../../stores/copilotUI';

// Create mock functions at module scope
const mockSendMessage = vi.fn();
const mockCancelStream = vi.fn();

// Mock the WebSocket manager
vi.mock('../api', () => ({
  getCopilotWebSocket: () => ({
    sendMessage: mockSendMessage,
    cancelStream: mockCancelStream,
    connect: vi.fn(),
    disconnect: vi.fn(),
    getState: vi.fn(() => 'connected'),
  }),
}));

describe('ChatInput', () => {
  beforeEach(() => {
    // Clear mock calls
    mockSendMessage.mockClear();
    mockCancelStream.mockClear();

    // Reset store state before each test
    useCopilotUIStore.setState({
      isStreaming: false,
      aiEnabled: true,
      wsConnected: true,
      error: null,
    });
  });

  it('sends message on Enter key', async () => {
    const user = userEvent.setup();

    render(<ChatInput page="Dashboard" pageContext={{}} />);

    const input = screen.getByRole('textbox', { name: /chat message input/i });
    await user.type(input, 'Hello world');
    await user.keyboard('{Enter}');

    expect(mockSendMessage).toHaveBeenCalledWith('Hello world', 'Dashboard', {});
  });

  it('creates newline on Shift+Enter', async () => {
    const user = userEvent.setup();

    render(<ChatInput page="Dashboard" pageContext={{}} />);

    const input = screen.getByRole('textbox', { name: /chat message input/i });
    await user.type(input, 'Line 1');
    await user.keyboard('{Shift>}{Enter}{/Shift}');
    await user.type(input, 'Line 2');

    // Input should contain both lines
    expect(input).toHaveValue('Line 1\nLine 2');
  });

  it('shows Cancel button when streaming', () => {
    useCopilotUIStore.setState({ isStreaming: true });

    render(<ChatInput page="Dashboard" pageContext={{}} />);

    // Cancel button should be visible
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    // Send button should not be visible
    expect(screen.queryByRole('button', { name: /send/i })).not.toBeInTheDocument();
  });

  it('is disabled when AI not configured', () => {
    useCopilotUIStore.setState({ aiEnabled: false });

    render(<ChatInput page="Dashboard" pageContext={{}} />);

    const input = screen.getByRole('textbox', { name: /chat message input/i });
    expect(input).toBeDisabled();
    expect(input).toHaveAttribute('placeholder', 'AI not configured');
  });

  it('rejects empty message', async () => {
    const user = userEvent.setup();

    render(<ChatInput page="Dashboard" pageContext={{}} />);

    const input = screen.getByRole('textbox', { name: /chat message input/i });
    // Type only whitespace
    await user.type(input, '   ');
    await user.keyboard('{Enter}');

    // sendMessage should not be called for empty/whitespace-only messages
    expect(mockSendMessage).not.toHaveBeenCalled();
  });

  it('disables send button when input is empty', () => {
    render(<ChatInput page="Dashboard" pageContext={{}} />);

    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).toBeDisabled();
  });

  it('calls cancelStream when Cancel button is clicked', async () => {
    const user = userEvent.setup();
    useCopilotUIStore.setState({ isStreaming: true });

    render(<ChatInput page="Dashboard" pageContext={{}} />);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(mockCancelStream).toHaveBeenCalled();
  });
});
