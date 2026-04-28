/**
 * Tests for AlertBanner component (Sprint 31.91 Session 5c).
 *
 * Mocks `useAlerts` so the banner is exercised in isolation without
 * spinning up a real WebSocket. Severity-rendering decision: banner
 * displays `critical` only — `warning` and `info` are toast-only (5d).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import type { Alert } from '../hooks/useAlerts';

// ---------------------------------------------------------------------------
// useAlerts mock (mutable per-test)
// ---------------------------------------------------------------------------

const mockState = {
  alerts: [] as Alert[],
  acknowledge: vi.fn(),
};

vi.mock('../hooks/useAlerts', () => ({
  useAlerts: () => ({
    alerts: mockState.alerts,
    connectionStatus: 'connected' as const,
    acknowledge: mockState.acknowledge,
  }),
}));

const { AlertBanner } = await import('./AlertBanner');

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    alert_id: 'a-1',
    alert_type: 'phantom_short',
    severity: 'critical',
    source: 'order_manager',
    message: 'Phantom short detected for AAPL',
    metadata: {},
    state: 'active',
    created_at_utc: new Date().toISOString(),
    acknowledged_at_utc: null,
    acknowledged_by: null,
    archived_at_utc: null,
    acknowledgment_reason: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AlertBanner', () => {
  beforeEach(() => {
    mockState.alerts = [];
    mockState.acknowledge = vi.fn().mockResolvedValue({
      alert_id: 'a-1',
      acknowledged_at_utc: 'now',
      acknowledged_by: 'operator',
      reason: 'r',
      audit_id: 1,
      state: 'acknowledged',
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when there are no alerts', () => {
    const { container } = render(<AlertBanner />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when only non-critical alerts are active (warning is toast-only)', () => {
    mockState.alerts = [
      makeAlert({ severity: 'warning', message: 'low-severity issue' }),
      makeAlert({ severity: 'info', message: 'fyi' }),
    ];
    const { container } = render(<AlertBanner />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when critical alert is acknowledged (state != active)', () => {
    mockState.alerts = [
      makeAlert({ state: 'acknowledged', acknowledged_by: 'operator' }),
    ];
    const { container } = render(<AlertBanner />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the banner for an active critical alert with role="alert"', () => {
    mockState.alerts = [makeAlert({ message: 'CRITICAL: phantom short on AAPL' })];
    render(<AlertBanner />);
    const banner = screen.getByRole('alert');
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent('Critical');
    expect(banner).toHaveTextContent('CRITICAL: phantom short on AAPL');
  });

  it('applies critical severity styling (bg-red-600)', () => {
    mockState.alerts = [makeAlert()];
    render(<AlertBanner />);
    const banner = screen.getByRole('alert');
    expect(banner.className).toContain('bg-red-600');
    expect(banner.className).toContain('border-red-700');
  });

  it('shows "+N more" when multiple critical alerts are active', () => {
    mockState.alerts = [
      makeAlert({ alert_id: 'a', created_at_utc: '2026-04-28T10:00:00Z' }),
      makeAlert({ alert_id: 'b', created_at_utc: '2026-04-28T10:05:00Z' }),
      makeAlert({ alert_id: 'c', created_at_utc: '2026-04-28T10:10:00Z' }),
    ];
    render(<AlertBanner />);
    expect(screen.getByText('+2 more')).toBeInTheDocument();
  });

  it('headline is the most-recently-created alert', () => {
    mockState.alerts = [
      makeAlert({
        alert_id: 'old',
        message: 'oldest message',
        created_at_utc: '2026-04-28T09:00:00Z',
      }),
      makeAlert({
        alert_id: 'mid',
        message: 'middle message',
        created_at_utc: '2026-04-28T10:00:00Z',
      }),
      makeAlert({
        alert_id: 'new',
        message: 'newest message',
        created_at_utc: '2026-04-28T11:00:00Z',
      }),
    ];
    render(<AlertBanner />);
    const banner = screen.getByRole('alert');
    expect(banner).toHaveTextContent('newest message');
  });

  it('clicking Acknowledge calls acknowledge() with alert_id, reason, operator_id', async () => {
    mockState.alerts = [makeAlert({ alert_id: 'target-id' })];
    render(<AlertBanner />);
    const button = screen.getByRole('button', { name: /acknowledge/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockState.acknowledge).toHaveBeenCalledWith(
        'target-id',
        expect.any(String),
        'operator',
      );
    });
    // Reason must be a non-empty string ≥10 chars (backend validator).
    const calledReason = mockState.acknowledge.mock.calls[0][1] as string;
    expect(calledReason.length).toBeGreaterThanOrEqual(10);
  });

  it('Acknowledge button is a real <button> element (keyboard-focusable)', () => {
    mockState.alerts = [makeAlert()];
    render(<AlertBanner />);
    const button = screen.getByRole('button', { name: /acknowledge/i });
    expect(button.tagName).toBe('BUTTON');
    expect(button).not.toHaveAttribute('disabled');
  });

  it('disappears synchronously when active critical alert list becomes empty (ack/auto-resolve)', () => {
    mockState.alerts = [makeAlert()];
    const { container, rerender } = render(<AlertBanner />);
    expect(container.firstChild).not.toBeNull();

    // Simulate WS push that drops the alert from the active list (ack or
    // auto-resolve transitions it to acknowledged/archived). The hook
    // surfaces the new list via re-render.
    mockState.alerts = [];
    rerender(<AlertBanner />);
    expect(container.firstChild).toBeNull();
  });
});
