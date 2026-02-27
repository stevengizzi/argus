/**
 * Tests for ThrottleOverrideDialog component.
 *
 * Sprint 21b, Session 8.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThrottleOverrideDialog } from './ThrottleOverrideDialog';
import { useOrchestratorUI } from '../../stores/orchestratorUI';

// Mock the mutation hook
vi.mock('../../hooks/useOrchestratorMutations', () => ({
  useThrottleOverrideMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

// Wrapper component with providers
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

describe('ThrottleOverrideDialog', () => {
  beforeEach(() => {
    // Reset the Zustand store before each test
    useOrchestratorUI.setState({
      overrideDialogOpen: false,
      overrideTargetStrategy: null,
    });
  });

  it('does not render when overrideDialogOpen is false', () => {
    render(
      <TestWrapper>
        <ThrottleOverrideDialog />
      </TestWrapper>
    );

    // Dialog should not be visible
    expect(screen.queryByText('Override Throttle')).not.toBeInTheDocument();
  });

  it('renders when store.overrideDialogOpen is true and validates reason length', () => {
    // Open the dialog
    useOrchestratorUI.setState({
      overrideDialogOpen: true,
      overrideTargetStrategy: 'orb_breakout',
    });

    render(
      <TestWrapper>
        <ThrottleOverrideDialog />
      </TestWrapper>
    );

    // Dialog should be visible
    expect(screen.getByText('Override Throttle')).toBeInTheDocument();

    // Strategy name should be shown
    expect(screen.getByText('ORB Breakout')).toBeInTheDocument();

    // Confirm button should be disabled initially (empty reason)
    const confirmButton = screen.getByRole('button', { name: /Confirm Override/i });
    expect(confirmButton).toBeDisabled();

    // Type a short reason (less than 10 chars)
    const reasonInput = screen.getByPlaceholderText(/Why are you overriding/);
    fireEvent.change(reasonInput, { target: { value: 'short' } });

    // Button should still be disabled
    expect(confirmButton).toBeDisabled();

    // Type a valid reason (10+ chars)
    fireEvent.change(reasonInput, { target: { value: 'This is a valid reason for override' } });

    // Button should now be enabled
    expect(confirmButton).not.toBeDisabled();
  });
});
