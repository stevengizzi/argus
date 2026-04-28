/**
 * Tests for AlertAcknowledgmentModal (Sprint 31.91 Session 5d).
 *
 * Per the verified backend contract (argus/api/routes/alerts.py):
 * - 200 normal/idempotent/late-ack — `AcknowledgeResult` returned. The
 *   idempotent path preserves the ORIGINAL acknowledger info, so
 *   detection of "already acknowledged from another tab" is via
 *   `acknowledged_by !== submitted operator_id`.
 * - 404 — hook returns null. Modal shows "no longer active" feedback.
 * - Other non-200 — hook throws. Modal shows error + Retry.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import type { Alert, AcknowledgeResult } from '../hooks/useAlerts';
import { AlertAcknowledgmentModal } from './AlertAcknowledgmentModal';

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

function makeAckResult(
  overrides: Partial<AcknowledgeResult> = {},
): AcknowledgeResult {
  return {
    alert_id: 'a-1',
    acknowledged_at_utc: '2026-04-28T12:00:30Z',
    acknowledged_by: 'operator',
    reason: 'investigated and confirmed',
    audit_id: 42,
    state: 'acknowledged',
    ...overrides,
  };
}

describe('AlertAcknowledgmentModal', () => {
  beforeEach(() => {
    // jsdom requires this to be re-enabled per test for focus checks.
    document.body.innerHTML = '';
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders dialog with role/labelling and focuses the textarea on mount', async () => {
    const onClose = vi.fn();
    const onSubmit = vi.fn();
    render(
      <AlertAcknowledgmentModal
        alert={makeAlert()}
        operatorId="operator"
        onClose={onClose}
        onSubmit={onSubmit}
      />,
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'alert-ack-modal-title');
    expect(screen.getByText('Acknowledge Alert')).toBeInTheDocument();
    expect(screen.getByText('phantom_short')).toBeInTheDocument();

    const textarea = screen.getByRole('textbox');
    await waitFor(() => {
      expect(document.activeElement).toBe(textarea);
    });
  });

  it('disables submit until reason has >=10 chars (trimmed)', () => {
    const onSubmit = vi.fn();
    render(
      <AlertAcknowledgmentModal
        alert={makeAlert()}
        operatorId="operator"
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    const submit = screen.getByRole('button', { name: /^acknowledge$/i });
    expect(submit).toBeDisabled();

    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: '123456789' } }); // 9 chars
    expect(submit).toBeDisabled();

    fireEvent.change(textarea, { target: { value: '1234567890' } }); // 10 chars
    expect(submit).toBeEnabled();

    // Whitespace-only padding should NOT count.
    fireEvent.change(textarea, { target: { value: '         x' } }); // 1 trimmed char
    expect(submit).toBeDisabled();
  });

  it('cancel calls onClose without invoking submit', () => {
    const onClose = vi.fn();
    const onSubmit = vi.fn();
    render(
      <AlertAcknowledgmentModal
        alert={makeAlert()}
        operatorId="operator"
        onClose={onClose}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('Escape key closes the modal', () => {
    const onClose = vi.fn();
    render(
      <AlertAcknowledgmentModal
        alert={makeAlert()}
        operatorId="operator"
        onClose={onClose}
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('successful submit displays audit-id confirmation', async () => {
    const onSubmit = vi
      .fn()
      .mockResolvedValue(makeAckResult({ audit_id: 99 }));
    render(
      <AlertAcknowledgmentModal
        alert={makeAlert()}
        operatorId="operator"
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'investigated the alert and confirmed' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^acknowledge$/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        'investigated the alert and confirmed',
        'operator',
      );
    });

    await screen.findByText(/audit ID: 99/i);
    // Submit button hides once outcome is shown.
    expect(
      screen.queryByRole('button', { name: /^acknowledge$/i }),
    ).not.toBeInTheDocument();
    // Cancel button now displays "Close" text (separate from the header
    // icon-button whose aria-label is also "Close"). Verify the footer
    // button specifically — it has the expected styling/role.
    const closeButtons = screen.getAllByRole('button', { name: /^close$/i });
    // One is the header X icon (aria-label="Close"), one is the footer
    // text button. We only need to confirm the footer button exists.
    expect(closeButtons.length).toBeGreaterThanOrEqual(1);
    const footerCloseButton = closeButtons.find(
      (b) => b.textContent?.trim() === 'Close',
    );
    expect(footerCloseButton).toBeDefined();
  });

  it('treats 404 (hook returns null) as "no longer active"', async () => {
    const onSubmit = vi.fn().mockResolvedValue(null);
    render(
      <AlertAcknowledgmentModal
        alert={makeAlert()}
        operatorId="operator"
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'investigated, no longer relevant' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^acknowledge$/i }));

    await screen.findByText(/no longer active/i);
  });

  it('handles duplicate-ack (200 with original acknowledger preserved)', async () => {
    const onSubmit = vi.fn().mockResolvedValue(
      makeAckResult({
        acknowledged_by: 'alice',
        audit_id: 7,
      }),
    );
    render(
      <AlertAcknowledgmentModal
        alert={makeAlert()}
        operatorId="bob"
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'duplicate ack from another tab' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^acknowledge$/i }));

    const success = await screen.findByRole('status');
    expect(success).toHaveTextContent(/audit ID: 7/i);
    expect(success).toHaveTextContent(/previously acknowledged by/i);
    expect(success).toHaveTextContent('alice');
  });

  it('shows error message + Retry on submit failure; retry re-invokes onSubmit', async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValueOnce(new Error('Acknowledge failed: HTTP 500'))
      .mockResolvedValueOnce(makeAckResult({ audit_id: 11 }));

    render(
      <AlertAcknowledgmentModal
        alert={makeAlert()}
        operatorId="operator"
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'investigated, will retry' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^acknowledge$/i }));

    const errBox = await screen.findByRole('alert');
    expect(errBox).toHaveTextContent(/HTTP 500/i);

    fireEvent.click(screen.getByRole('button', { name: /^retry$/i }));

    await screen.findByText(/audit ID: 11/i);
    expect(onSubmit).toHaveBeenCalledTimes(2);
  });
});
