/**
 * AlertsPanel tests (Sprint 31.91 Session 5e).
 *
 * Mocks `useAlerts`, `useAlertHistory`, and `useAlertAuditTrail` so the
 * panel can be exercised in isolation without a WebSocket or real REST
 * traffic. Same isolation pattern as AlertBanner.test.tsx.
 *
 * Covers (D13 + AC-D13):
 *   1. Active alerts render with table rows.
 *   2. Historical alerts render via date-range hook.
 *   3. Sort by severity / source / symbol / time.
 *   4. Filter by severity / source / symbol.
 *   5. Audit trail visible per alert.
 *   6. Click-through to detail modal renders metadata + audit.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import type {
  Alert,
  AlertAuditEntry,
  AlertHistoryRange,
} from '../hooks/useAlerts';

// ---------------------------------------------------------------------------
// Mock state
// ---------------------------------------------------------------------------

interface MockState {
  active: Alert[];
  history: Alert[];
  audit: AlertAuditEntry[];
  lastHistoryRange: AlertHistoryRange | null;
  lastAuditId: string | null;
}

const mockState: MockState = {
  active: [],
  history: [],
  audit: [],
  lastHistoryRange: null,
  lastAuditId: null,
};

vi.mock('../hooks/useAlerts', async () => {
  const actual =
    await vi.importActual<typeof import('../hooks/useAlerts')>(
      '../hooks/useAlerts',
    );
  return {
    ...actual,
    useAlerts: () => ({
      alerts: mockState.active,
      connectionStatus: 'connected' as const,
      acknowledge: vi.fn(),
    }),
    useAlertHistory: (range: AlertHistoryRange) => {
      mockState.lastHistoryRange = range;
      return { data: mockState.history, isLoading: false };
    },
    useAlertAuditTrail: (alert_id: string | null) => {
      mockState.lastAuditId = alert_id;
      return {
        data: alert_id ? mockState.audit : [],
        isLoading: false,
      };
    },
  };
});

const { AlertsPanel } = await import('./AlertsPanel');

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    alert_id: 'a-1',
    alert_type: 'phantom_short',
    severity: 'critical',
    source: 'order_manager',
    message: 'Phantom short detected',
    metadata: { symbol: 'AAPL', shares: 100 },
    state: 'active',
    created_at_utc: '2026-04-28T10:00:00Z',
    acknowledged_at_utc: null,
    acknowledged_by: null,
    archived_at_utc: null,
    acknowledgment_reason: null,
    ...overrides,
  };
}

function makeAuditEntry(
  overrides: Partial<AlertAuditEntry> = {},
): AlertAuditEntry {
  return {
    audit_id: 1,
    timestamp_utc: '2026-04-28T10:05:00Z',
    alert_id: 'a-1',
    operator_id: 'operator',
    reason: 'investigated and accepted',
    audit_kind: 'ack',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AlertsPanel', () => {
  beforeEach(() => {
    mockState.active = [];
    mockState.history = [];
    mockState.audit = [];
    mockState.lastHistoryRange = null;
    mockState.lastAuditId = null;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders active alerts as table rows', () => {
    mockState.active = [
      makeAlert({ alert_id: 'a-1', message: 'first active' }),
      makeAlert({
        alert_id: 'a-2',
        message: 'second active',
        severity: 'warning',
        metadata: { symbol: 'TSLA' },
      }),
    ];
    render(<AlertsPanel />);
    const activeTable = screen.getByTestId('alerts-table-active');
    expect(within(activeTable).getByText('first active')).toBeInTheDocument();
    expect(within(activeTable).getByText('second active')).toBeInTheDocument();
    expect(
      screen.getByTestId('alerts-table-active-row-a-1'),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId('alerts-table-active-row-a-2'),
    ).toBeInTheDocument();
  });

  it('renders historical alerts via the date-range hook with default 7-day range', () => {
    mockState.history = [
      makeAlert({
        alert_id: 'h-1',
        message: 'historical alert',
        state: 'archived',
      }),
    ];
    render(<AlertsPanel />);

    // Hook was invoked and produced a from/to ISO range; default ~7 days back.
    expect(mockState.lastHistoryRange).not.toBeNull();
    expect(mockState.lastHistoryRange?.from).toMatch(
      /^\d{4}-\d{2}-\d{2}T00:00:00Z$/,
    );
    expect(mockState.lastHistoryRange?.to).toMatch(
      /^\d{4}-\d{2}-\d{2}T23:59:59Z$/,
    );

    const historyTable = screen.getByTestId('alerts-table-history');
    expect(
      within(historyTable).getByText('historical alert'),
    ).toBeInTheDocument();
  });

  it('updates the history range when the date pickers change', () => {
    mockState.history = [];
    render(<AlertsPanel />);
    const fromInput = screen.getByTestId('history-from') as HTMLInputElement;
    fireEvent.change(fromInput, { target: { value: '2026-04-01' } });
    expect(mockState.lastHistoryRange?.from).toBe('2026-04-01T00:00:00Z');

    const toInput = screen.getByTestId('history-to') as HTMLInputElement;
    fireEvent.change(toInput, { target: { value: '2026-04-15' } });
    expect(mockState.lastHistoryRange?.to).toBe('2026-04-15T23:59:59Z');
  });

  it('sorts active alerts by severity / source / symbol when headers clicked', () => {
    mockState.active = [
      makeAlert({
        alert_id: 'low',
        severity: 'info',
        source: 'zeta_source',
        metadata: { symbol: 'ZETA' },
        message: 'low priority',
      }),
      makeAlert({
        alert_id: 'high',
        severity: 'critical',
        source: 'alpha_source',
        metadata: { symbol: 'ALPHA' },
        message: 'high priority',
      }),
      makeAlert({
        alert_id: 'mid',
        severity: 'warning',
        source: 'mid_source',
        metadata: { symbol: 'MID' },
        message: 'mid priority',
      }),
    ];
    render(<AlertsPanel />);

    function rowOrder(): string[] {
      const table = screen.getByTestId('alerts-table-active');
      const rows = within(table).getAllByRole('button');
      // Filter to row buttons (not sort headers): rows have data-testid
      // matching alerts-table-active-row-*.
      return rows
        .filter((el) =>
          el
            .getAttribute('data-testid')
            ?.startsWith('alerts-table-active-row-'),
        )
        .map((el) =>
          el.getAttribute('data-testid')!.replace(
            'alerts-table-active-row-',
            '',
          ),
        );
    }

    // Severity sort: critical → warning → info.
    fireEvent.click(screen.getByTestId('alerts-table-active-sort-severity'));
    expect(rowOrder()).toEqual(['high', 'mid', 'low']);

    // Source sort: alpha < mid < zeta lexicographic.
    fireEvent.click(screen.getByTestId('alerts-table-active-sort-source'));
    expect(rowOrder()).toEqual(['high', 'mid', 'low']);

    // Symbol sort: ALPHA < MID < ZETA lexicographic.
    fireEvent.click(screen.getByTestId('alerts-table-active-sort-symbol'));
    expect(rowOrder()).toEqual(['high', 'mid', 'low']);
  });

  it('filters active alerts by severity / source / symbol', () => {
    mockState.active = [
      makeAlert({
        alert_id: 'crit-aapl',
        severity: 'critical',
        source: 'order_manager',
        metadata: { symbol: 'AAPL' },
      }),
      makeAlert({
        alert_id: 'warn-tsla',
        severity: 'warning',
        source: 'risk_manager',
        metadata: { symbol: 'TSLA' },
      }),
      makeAlert({
        alert_id: 'info-msft',
        severity: 'info',
        source: 'order_manager',
        metadata: { symbol: 'MSFT' },
      }),
    ];
    render(<AlertsPanel />);

    fireEvent.change(screen.getByTestId('filter-severity'), {
      target: { value: 'critical' },
    });
    expect(screen.queryByTestId('alerts-table-active-row-crit-aapl')).toBeInTheDocument();
    expect(screen.queryByTestId('alerts-table-active-row-warn-tsla')).not.toBeInTheDocument();
    expect(screen.queryByTestId('alerts-table-active-row-info-msft')).not.toBeInTheDocument();

    fireEvent.change(screen.getByTestId('filter-severity'), {
      target: { value: 'all' },
    });
    fireEvent.change(screen.getByTestId('filter-source'), {
      target: { value: 'risk_manager' },
    });
    expect(screen.queryByTestId('alerts-table-active-row-crit-aapl')).not.toBeInTheDocument();
    expect(screen.queryByTestId('alerts-table-active-row-warn-tsla')).toBeInTheDocument();
    expect(screen.queryByTestId('alerts-table-active-row-info-msft')).not.toBeInTheDocument();

    fireEvent.change(screen.getByTestId('filter-source'), {
      target: { value: 'all' },
    });
    fireEvent.change(screen.getByTestId('filter-symbol'), {
      target: { value: 'msft' },
    });
    expect(screen.queryByTestId('alerts-table-active-row-info-msft')).toBeInTheDocument();
    expect(screen.queryByTestId('alerts-table-active-row-crit-aapl')).not.toBeInTheDocument();
    expect(screen.queryByTestId('alerts-table-active-row-warn-tsla')).not.toBeInTheDocument();
  });

  it('opens detail view with metadata and audit trail when a row is clicked', () => {
    const alert = makeAlert({
      alert_id: 'detail-1',
      metadata: { symbol: 'NVDA', shares: 250, ratio: 2.0 },
    });
    mockState.active = [alert];
    mockState.audit = [
      makeAuditEntry({
        audit_id: 11,
        alert_id: 'detail-1',
        audit_kind: 'ack',
        reason: 'first acknowledgment',
      }),
      makeAuditEntry({
        audit_id: 12,
        alert_id: 'detail-1',
        audit_kind: 'duplicate_ack',
        reason: 'duplicate from second operator',
      }),
    ];
    render(<AlertsPanel />);

    fireEvent.click(screen.getByTestId('alerts-table-active-row-detail-1'));

    // Modal opens.
    const dialog = screen.getByTestId('alert-detail-view');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');

    // Metadata renders as JSON.
    const metadata = screen.getByTestId('alert-detail-metadata');
    expect(metadata.textContent).toContain('NVDA');
    expect(metadata.textContent).toContain('250');

    // Audit hook was called with the right alert_id and entries render.
    expect(mockState.lastAuditId).toBe('detail-1');
    const auditList = screen.getByTestId('alert-detail-audit');
    expect(within(auditList).getByText(/first acknowledgment/)).toBeInTheDocument();
    expect(
      within(auditList).getByText(/duplicate from second operator/),
    ).toBeInTheDocument();
  });

  it('renders audit-empty placeholder when an alert has no audit entries', () => {
    const alert = makeAlert({ alert_id: 'no-audit' });
    mockState.active = [alert];
    mockState.audit = [];
    render(<AlertsPanel />);

    fireEvent.click(screen.getByTestId('alerts-table-active-row-no-audit'));
    expect(screen.getByTestId('alert-detail-audit-empty')).toBeInTheDocument();
  });

  it('closes the detail view when Close is clicked', () => {
    mockState.active = [makeAlert({ alert_id: 'close-me' })];
    render(<AlertsPanel />);
    fireEvent.click(screen.getByTestId('alerts-table-active-row-close-me'));
    expect(screen.getByTestId('alert-detail-view')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(screen.queryByTestId('alert-detail-view')).not.toBeInTheDocument();
  });
});
