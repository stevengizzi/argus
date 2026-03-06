/**
 * Tests for ActionCard component.
 *
 * Sprint 22, Session 5.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ActionCard } from '../ActionCard';
import type { ProposalState } from '../../../stores/copilotUI';

// Mock the copilot store
vi.mock('../../../stores/copilotUI', () => ({
  useCopilotUIStore: vi.fn(() => ({
    updateProposal: vi.fn(),
    notificationsEnabled: false, // Disable sounds in tests
  })),
}));

// Mock the notifications utility
vi.mock('../../../utils/notifications', () => ({
  playProposalNotification: vi.fn(),
  playExpiryWarning: vi.fn(),
  initializeAudioContext: vi.fn(),
}));

describe('ActionCard', () => {
  const mockOnApprove = vi.fn().mockResolvedValue(undefined);
  const mockOnReject = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const createProposal = (overrides: Partial<ProposalState> = {}): ProposalState => ({
    id: 'test-proposal-1',
    toolName: 'propose_allocation_change',
    toolInput: {
      strategy_id: 'orb_breakout',
      new_allocation_pct: 35,
      reason: 'Market conditions favor this strategy',
    },
    status: 'pending',
    expiresAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(), // 5 minutes from now
    ...overrides,
  });

  it('renders pending state with Approve/Reject buttons', () => {
    const proposal = createProposal();

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Should show Allocation Change label
    expect(screen.getByText('Allocation Change')).toBeInTheDocument();

    // Should show description
    expect(screen.getByText(/orb_breakout.*35%/)).toBeInTheDocument();

    // Should show reason
    expect(screen.getByText(/Market conditions favor this strategy/)).toBeInTheDocument();

    // Should have Approve and Reject buttons
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();

    // Should have amber border for pending
    const card = screen.getByTestId('action-card');
    expect(card).toHaveAttribute('data-status', 'pending');
  });

  it('renders executed state with result', () => {
    const proposal = createProposal({
      status: 'executed',
      result: { message: 'Allocation changed successfully' },
    });

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Should show Executed badge
    expect(screen.getByText('Executed')).toBeInTheDocument();

    // Should show result message
    expect(screen.getByText('Allocation changed successfully')).toBeInTheDocument();

    // Should NOT have Approve/Reject buttons
    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument();
  });

  it('renders expired state dimmed', () => {
    const proposal = createProposal({
      status: 'expired',
      expiresAt: new Date(Date.now() - 1000).toISOString(), // Expired
    });

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Should show Expired badge
    expect(screen.getByText('Expired')).toBeInTheDocument();

    // Card should be dimmed
    const card = screen.getByTestId('action-card');
    expect(card).toHaveClass('opacity-60');
  });

  it('renders failed state with reason', () => {
    const proposal = createProposal({
      status: 'failed',
      failureReason: 'Execution blocked — regime changed since proposal',
    });

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Should show Failed badge
    expect(screen.getByText('Failed')).toBeInTheDocument();

    // Should show failure reason
    expect(
      screen.getByText('Execution blocked — regime changed since proposal')
    ).toBeInTheDocument();
  });

  it('Approve click shows confirmation dialog', async () => {
    const proposal = createProposal();

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Click Approve button
    fireEvent.click(screen.getByRole('button', { name: /approve/i }));

    // Confirmation dialog should appear
    await waitFor(() => {
      expect(screen.getByText('Confirm Action')).toBeInTheDocument();
    });

    // Should show action description
    expect(screen.getByText(/change orb_breakout allocation to 35%/)).toBeInTheDocument();

    // Should have Confirm and Cancel buttons
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('displays countdown timer for pending proposals', () => {
    const proposal = createProposal({
      expiresAt: new Date(Date.now() + 3 * 60 * 1000 + 30 * 1000).toISOString(), // 3:30 remaining
    });

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Should show countdown (approximately 3:30, may be 3:29 due to timing)
    expect(screen.getByText(/3:\d{2}/)).toBeInTheDocument();
  });

  it('renders different visual for each tool type', () => {
    const toolTypes = [
      { toolName: 'propose_allocation_change', label: 'Allocation Change' },
      { toolName: 'propose_risk_param_change', label: 'Risk Parameter' },
      { toolName: 'propose_strategy_suspend', label: 'Suspend Strategy' },
      { toolName: 'propose_strategy_resume', label: 'Resume Strategy' },
      { toolName: 'generate_report', label: 'Report' },
    ];

    for (const { toolName, label } of toolTypes) {
      const { unmount } = render(
        <ActionCard
          proposal={createProposal({ toolName })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it('renders approved state with executing spinner', () => {
    const proposal = createProposal({
      status: 'approved',
    });

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Should show Approved badge
    expect(screen.getByText(/Approved/)).toBeInTheDocument();

    // Should show Executing message
    expect(screen.getByText('Executing...')).toBeInTheDocument();
  });

  it('renders rejected state dimmed', () => {
    const proposal = createProposal({
      status: 'rejected',
    });

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Should show Rejected badge
    expect(screen.getByText('Rejected')).toBeInTheDocument();

    // Card should be dimmed
    const card = screen.getByTestId('action-card');
    expect(card).toHaveClass('opacity-60');
  });

  it('shows keyboard hint text for pending proposals', () => {
    const proposal = createProposal();

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Should show keyboard hint
    expect(screen.getByText('Y to approve · N to reject')).toBeInTheDocument();
  });

  it('Y key opens confirmation dialog for pending proposal', async () => {
    const proposal = createProposal();

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Press Y key
    fireEvent.keyDown(window, { key: 'y' });

    // Confirmation dialog should appear
    await waitFor(() => {
      expect(screen.getByText('Confirm Action')).toBeInTheDocument();
    });
  });

  it('N key opens reject dialog for pending proposal', async () => {
    const proposal = createProposal();

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Press N key
    fireEvent.keyDown(window, { key: 'n' });

    // Reject dialog should appear
    await waitFor(() => {
      expect(screen.getByText('Reject Action')).toBeInTheDocument();
    });
  });

  it('renders View Report button for executed generate_report', async () => {
    const proposal = createProposal({
      toolName: 'generate_report',
      toolInput: {
        report_type: 'daily_summary',
      },
      status: 'executed',
      result: {
        report_type: 'daily_summary',
        content: '# Daily Summary\n\nThis is the report content.',
        date: '2026-03-07',
        saved: true,
      },
    });

    render(
      <ActionCard
        proposal={proposal}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    // Should show View Report button
    expect(screen.getByText('View Report')).toBeInTheDocument();

    // Click to expand
    fireEvent.click(screen.getByText('View Report'));

    // Should show report content
    await waitFor(() => {
      expect(screen.getByText(/Daily Summary/)).toBeInTheDocument();
    });

    // Should now show Hide Report button
    expect(screen.getByText('Hide Report')).toBeInTheDocument();
  });
});
