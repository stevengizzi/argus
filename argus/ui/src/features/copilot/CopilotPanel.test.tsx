/**
 * Tests for CopilotPanel component.
 *
 * Sprint 21d, Session 11.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CopilotPanel } from './CopilotPanel';
import { useCopilotUIStore } from '../../stores/copilotUI';

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

    expect(screen.queryByText('AI Copilot')).not.toBeInTheDocument();
  });

  it('renders panel content when open', () => {
    useCopilotUIStore.setState({ isOpen: true });

    render(
      <TestWrapper>
        <CopilotPanel />
      </TestWrapper>
    );

    // Header (there are two "AI Copilot" texts - one in header, one in placeholder)
    expect(screen.getAllByText('AI Copilot')).toHaveLength(2);

    // Placeholder content
    expect(screen.getByText('Contextual AI assistant activating Sprint 22. Soon you\'ll chat with Claude here — page-aware, with full system knowledge.')).toBeInTheDocument();

    // Feature list
    expect(screen.getByText('Answer questions about any system data')).toBeInTheDocument();

    // Disabled input
    expect(screen.getByPlaceholderText('Activating Sprint 22...')).toBeDisabled();
  });

  it('shows context indicator with current page name', () => {
    useCopilotUIStore.setState({ isOpen: true });

    render(
      <TestWrapper initialPath="/trades">
        <CopilotPanel />
      </TestWrapper>
    );

    expect(screen.getByText('Page: Trade Log')).toBeInTheDocument();
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
});
