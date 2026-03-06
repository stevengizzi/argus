/**
 * Tests for CopilotPanel component.
 *
 * Sprint 21d, Session 11.
 * Sprint 22, Session 4a — Updated for live chat integration.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CopilotPanel } from './CopilotPanel';
import { useCopilotUIStore } from '../../stores/copilotUI';

// Mock the API module to prevent actual API calls
vi.mock('./api', () => ({
  getCopilotWebSocket: vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    sendMessage: vi.fn(),
    cancelStream: vi.fn(),
    getState: vi.fn(() => 'disconnected'),
  })),
  checkAIStatus: vi.fn().mockResolvedValue(false),
  loadTodayConversation: vi.fn().mockResolvedValue(undefined),
}));

// Wrapper with router
function TestWrapper({ children, initialPath = '/' }: { children: React.ReactNode; initialPath?: string }) {
  return (
    <MemoryRouter initialEntries={[initialPath]}>
      {children}
    </MemoryRouter>
  );
}

describe('CopilotPanel', () => {
  beforeEach(() => {
    // Reset the Zustand store before each test
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
    // Reset body overflow
    document.body.style.overflow = '';
  });

  it('renders nothing when closed', () => {
    render(
      <TestWrapper>
        <CopilotPanel />
      </TestWrapper>
    );

    expect(screen.queryByText('ARGUS Copilot')).not.toBeInTheDocument();
  });

  it('renders panel content when open', () => {
    useCopilotUIStore.setState({ isOpen: true });

    render(
      <TestWrapper>
        <CopilotPanel />
      </TestWrapper>
    );

    // Header
    expect(screen.getByText('ARGUS Copilot')).toBeInTheDocument();

    // AI Not Configured state (since aiEnabled is false)
    expect(screen.getByText('AI Not Configured')).toBeInTheDocument();

    // Chat input should be disabled
    expect(screen.getByPlaceholderText('AI not configured')).toBeDisabled();
  });

  it('shows page name in header', () => {
    useCopilotUIStore.setState({ isOpen: true });

    render(
      <TestWrapper initialPath="/trades">
        <CopilotPanel />
      </TestWrapper>
    );

    // Header shows "ARGUS Copilot • Trade Log"
    expect(screen.getByText(/• Trade Log/)).toBeInTheDocument();
  });

  it('closes when close button is clicked', () => {
    useCopilotUIStore.setState({ isOpen: true });
    const closeSpy = vi.spyOn(useCopilotUIStore.getState(), 'close');

    render(
      <TestWrapper>
        <CopilotPanel />
      </TestWrapper>
    );

    const closeButton = screen.getByRole('button', { name: /close copilot/i });
    fireEvent.click(closeButton);

    expect(closeSpy).toHaveBeenCalled();
  });

  it('shows empty state when AI enabled but no messages', () => {
    useCopilotUIStore.setState({
      isOpen: true,
      aiEnabled: true,
      messages: [],
    });

    render(
      <TestWrapper>
        <CopilotPanel />
      </TestWrapper>
    );

    expect(screen.getByText('Start a conversation')).toBeInTheDocument();
  });

  it('shows error banner when error exists', () => {
    useCopilotUIStore.setState({
      isOpen: true,
      aiEnabled: true,
      error: 'Connection failed',
    });

    render(
      <TestWrapper>
        <CopilotPanel />
      </TestWrapper>
    );

    expect(screen.getByText('Connection failed')).toBeInTheDocument();
  });
});
