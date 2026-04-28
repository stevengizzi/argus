/**
 * Tests for AlertToastStack + AlertToast (Sprint 31.91 Session 5d).
 *
 * Mocks `useAlerts` so the toast surface is exercised in isolation
 * without spinning up a real WebSocket. Uses the same mutable mockState
 * pattern as AlertBanner.test.tsx.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from '@testing-library/react';
import type { Alert, AcknowledgeResult } from '../hooks/useAlerts';

const mockState = {
  alerts: [] as Alert[],
  acknowledge: vi.fn() as ReturnType<typeof vi.fn>,
};

vi.mock('../hooks/useAlerts', () => ({
  useAlerts: () => ({
    alerts: mockState.alerts,
    connectionStatus: 'connected' as const,
    acknowledge: mockState.acknowledge,
  }),
}));

const { AlertToastStack } = await import('./AlertToast');

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    alert_id: 'a-1',
    alert_type: 'phantom_short',
    severity: 'critical',
    source: 'order_manager',
    message: 'Phantom short detected for AAPL',
    metadata: {},
    state: 'active',
    created_at_utc: '2026-04-28T12:00:00Z',
    acknowledged_at_utc: null,
    acknowledged_by: null,
    archived_at_utc: null,
    acknowledgment_reason: null,
    ...overrides,
  };
}

function defaultAckResult(): AcknowledgeResult {
  return {
    alert_id: 'a-1',
    acknowledged_at_utc: '2026-04-28T12:00:30Z',
    acknowledged_by: 'operator',
    reason: 'r',
    audit_id: 1,
    state: 'acknowledged',
  };
}

describe('AlertToastStack', () => {
  beforeEach(() => {
    mockState.alerts = [];
    mockState.acknowledge = vi.fn().mockResolvedValue(defaultAckResult());
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when no critical-active alerts are present', () => {
    mockState.alerts = [
      makeAlert({ severity: 'warning' }),
      makeAlert({ alert_id: 'b', state: 'acknowledged' }),
    ];
    render(<AlertToastStack />);
    // Region renders but contains no toasts.
    expect(screen.queryByTestId(/^alert-toast-/)).not.toBeInTheDocument();
  });

  it('renders a toast for an active critical alert with message + Acknowledge button', () => {
    mockState.alerts = [
      makeAlert({
        alert_id: 'a-1',
        message: 'Phantom short detected for AAPL',
      }),
    ];
    render(<AlertToastStack />);

    const toast = screen.getByTestId('alert-toast-a-1');
    expect(toast).toHaveTextContent('phantom_short');
    expect(toast).toHaveTextContent('Phantom short detected for AAPL');
    expect(
      within(toast).getByRole('button', { name: /acknowledge/i }),
    ).toBeInTheDocument();
  });

  it('toast unmounts when alert transitions out of critical-active', () => {
    mockState.alerts = [makeAlert({ alert_id: 'a-1' })];
    const { rerender } = render(<AlertToastStack />);
    expect(screen.getByTestId('alert-toast-a-1')).toBeInTheDocument();

    // WS pushes alert_acknowledged → hook surfaces the new state. Toast
    // re-renders, this alert filters out, toast unmounts.
    mockState.alerts = [
      makeAlert({ alert_id: 'a-1', state: 'acknowledged' }),
    ];
    rerender(<AlertToastStack />);
    expect(screen.queryByTestId('alert-toast-a-1')).not.toBeInTheDocument();
  });

  it('clicking Acknowledge opens the modal with focus on textarea', async () => {
    mockState.alerts = [makeAlert({ alert_id: 'a-1' })];
    render(<AlertToastStack />);

    fireEvent.click(
      within(screen.getByTestId('alert-toast-a-1')).getByRole('button', {
        name: /acknowledge/i,
      }),
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');

    const textarea = screen.getByRole('textbox');
    await waitFor(() => {
      expect(document.activeElement).toBe(textarea);
    });
  });

  it('caps visible toasts at 5 and drops the oldest by created_at_utc', () => {
    // Six critical-active alerts spanning 12:00 → 12:05.
    const times = [
      '2026-04-28T12:00:00Z',
      '2026-04-28T12:01:00Z',
      '2026-04-28T12:02:00Z',
      '2026-04-28T12:03:00Z',
      '2026-04-28T12:04:00Z',
      '2026-04-28T12:05:00Z',
    ];
    mockState.alerts = times.map((t, i) =>
      makeAlert({
        alert_id: `a-${i}`,
        created_at_utc: t,
        message: `msg ${i}`,
      }),
    );

    render(<AlertToastStack />);

    const toasts = screen.getAllByTestId(/^alert-toast-/);
    expect(toasts).toHaveLength(5);

    // Oldest (a-0, 12:00) is dropped.
    expect(screen.queryByTestId('alert-toast-a-0')).not.toBeInTheDocument();

    // Newest (a-5, 12:05) is rendered first in DOM order (top of stack).
    expect(toasts[0]).toHaveAttribute('data-testid', 'alert-toast-a-5');
    // Other 4 newest are present.
    for (const id of ['a-1', 'a-2', 'a-3', 'a-4', 'a-5']) {
      expect(screen.getByTestId(`alert-toast-${id}`)).toBeInTheDocument();
    }
  });

  it('cancelling the modal leaves the toast visible (alert still active)', () => {
    mockState.alerts = [makeAlert({ alert_id: 'a-1' })];
    render(<AlertToastStack />);

    fireEvent.click(
      within(screen.getByTestId('alert-toast-a-1')).getByRole('button', {
        name: /acknowledge/i,
      }),
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByTestId('alert-toast-a-1')).toBeInTheDocument();
    // Hook's acknowledge was never called.
    expect(mockState.acknowledge).not.toHaveBeenCalled();
  });

  it('successful acknowledge through modal calls hook with alert_id, reason, operator_id', async () => {
    mockState.alerts = [
      makeAlert({ alert_id: 'target-id', alert_type: 'phantom_short' }),
    ];
    render(<AlertToastStack />);

    fireEvent.click(
      within(screen.getByTestId('alert-toast-target-id')).getByRole('button', {
        name: /acknowledge/i,
      }),
    );

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'flatten verified, manual unwind complete' },
    });
    // Multiple "Acknowledge" buttons exist (toast + modal); scope to dialog.
    fireEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', {
        name: /^acknowledge$/i,
      }),
    );

    await waitFor(() => {
      expect(mockState.acknowledge).toHaveBeenCalledWith(
        'target-id',
        'flatten verified, manual unwind complete',
        'operator',
      );
    });
  });

  it('network failure on submit shows error + Retry; retry re-invokes hook', async () => {
    mockState.alerts = [makeAlert({ alert_id: 'a-1' })];
    mockState.acknowledge = vi
      .fn()
      .mockRejectedValueOnce(new Error('Acknowledge failed: HTTP 500'))
      .mockResolvedValueOnce(defaultAckResult());

    render(<AlertToastStack />);

    fireEvent.click(
      within(screen.getByTestId('alert-toast-a-1')).getByRole('button', {
        name: /acknowledge/i,
      }),
    );

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'investigated, will retry' },
    });
    const dialog = screen.getByRole('dialog');
    fireEvent.click(
      within(dialog).getByRole('button', { name: /^acknowledge$/i }),
    );

    const errBox = await screen.findByRole('alert');
    expect(errBox).toHaveTextContent(/HTTP 500/i);

    fireEvent.click(
      within(dialog).getByRole('button', { name: /^retry$/i }),
    );

    await screen.findByText(/audit ID: 1/i);
    expect(mockState.acknowledge).toHaveBeenCalledTimes(2);
  });
});
