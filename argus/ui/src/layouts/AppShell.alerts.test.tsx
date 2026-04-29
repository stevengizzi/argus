/**
 * Cross-page integration tests for AlertBanner + AlertToastStack mounted
 * at the AppShell layout level (Sprint 31.91 Session 5e — D13).
 *
 * Regression invariant 17 (sprint-spec): the banner persists across page
 * navigation. Test 1 ("AlertBanner persists across page navigation") is
 * the structural pin for the cross-page mount contract — it is the test
 * that fails if the AppShell mount is reverted to a per-page mount.
 *
 * Approach:
 *   - Mock heavy AppShell dependencies (Sidebar, MobileNav, store hooks,
 *     copilot, symbol panel) consistent with AppShell.test.tsx.
 *   - Mock `useAlerts` to provide a controlled active-alert list.
 *   - Render `<AppShell />` inside a `MemoryRouter` and a `Routes`
 *     definition that exercises three pages (Dashboard / TradeLog /
 *     Performance) as plain `<div>` placeholders. AppShell uses
 *     `useOutlet()` to render the matched route's element.
 *   - Navigate via the History API (`MemoryRouter` initial-entries pop)
 *     and assert the banner remains in the DOM.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import {
  MemoryRouter,
  Routes,
  Route,
  useNavigate,
} from 'react-router-dom';
import type { Alert } from '../hooks/useAlerts';

// ---------------------------------------------------------------------------
// Heavy-dependency mocks (mirror AppShell.test.tsx)
// ---------------------------------------------------------------------------

vi.mock('./Sidebar', () => ({ Sidebar: () => <div data-testid="sidebar" /> }));
vi.mock('./MobileNav', () => ({
  MobileNav: () => <div data-testid="mobile-nav" />,
}));
vi.mock('../stores/live', () => ({
  useLiveStore: (sel: (s: { connect: () => void; disconnect: () => void }) => unknown) =>
    sel({ connect: vi.fn(), disconnect: vi.fn() }),
}));
vi.mock('../stores/copilotUI', () => ({
  useCopilotUIStore: (sel: (s: { toggle: () => void }) => unknown) =>
    sel({ toggle: vi.fn() }),
}));
vi.mock('../features/symbol', () => ({
  SymbolDetailPanel: () => null,
}));
vi.mock('../features/copilot', () => ({
  CopilotPanel: () => null,
  CopilotButton: () => null,
}));

// ---------------------------------------------------------------------------
// useAlerts mock — drives the banner + toast via mockState.
// ---------------------------------------------------------------------------

const mockAcknowledge = vi.fn().mockResolvedValue({
  alert_id: 'crit-1',
  acknowledged_at_utc: 'now',
  acknowledged_by: 'operator',
  reason: 'r',
  audit_id: 1,
  state: 'acknowledged',
});

const mockState = {
  alerts: [] as Alert[],
};

vi.mock('../hooks/useAlerts', () => ({
  useAlerts: () => ({
    alerts: mockState.alerts,
    connectionStatus: 'connected' as const,
    acknowledge: mockAcknowledge,
  }),
}));

// AlertAcknowledgmentModal is rendered when a toast is clicked. We don't
// need to exercise its internals here.
vi.mock('../components/AlertAcknowledgmentModal', () => ({
  AlertAcknowledgmentModal: () => null,
}));

// ---------------------------------------------------------------------------
// Imports under test (after mocks)
// ---------------------------------------------------------------------------

const { AppShell } = await import('./AppShell');

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    alert_id: 'crit-1',
    alert_type: 'phantom_short',
    severity: 'critical',
    source: 'order_manager',
    message: 'CRITICAL: phantom short on AAPL',
    metadata: { symbol: 'AAPL' },
    state: 'active',
    created_at_utc: '2026-04-28T10:00:00Z',
    acknowledged_at_utc: null,
    acknowledged_by: null,
    archived_at_utc: null,
    acknowledgment_reason: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Test harness — App tree with three plain-div pages and a Navigator hook.
// ---------------------------------------------------------------------------

let navigateRef: ReturnType<typeof useNavigate> | null = null;

function CaptureNavigate() {
  navigateRef = useNavigate();
  return null;
}

function renderAppWithRoutes(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <CaptureNavigate />
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<div data-testid="page-dashboard">Dashboard</div>} />
          <Route
            path="trades"
            element={<div data-testid="page-trades">TradeLog</div>}
          />
          <Route
            path="performance"
            element={<div data-testid="page-performance">Performance</div>}
          />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AppShell — cross-page alert observability mount (Session 5e)', () => {
  beforeEach(() => {
    mockState.alerts = [];
    navigateRef = null;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // Regression invariant 17 — the banner persists across page navigation.
  it('AlertBanner persists across page navigation Dashboard → TradeLog → Performance', () => {
    mockState.alerts = [makeAlert()];
    renderAppWithRoutes('/');

    // Sanity: starts on Dashboard with the banner visible.
    expect(screen.getByTestId('page-dashboard')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Navigate to TradeLog; banner remains.
    act(() => {
      navigateRef!('/trades');
    });
    expect(screen.getByTestId('page-trades')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Navigate to Performance; banner remains.
    act(() => {
      navigateRef!('/performance');
    });
    expect(screen.getByTestId('page-performance')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('AlertToast appears on TradeLog page when a critical alert is active', () => {
    mockState.alerts = [];
    const { rerender } = renderAppWithRoutes('/');

    // Navigate to TradeLog with no alerts — no toast yet.
    act(() => {
      navigateRef!('/trades');
    });
    expect(screen.getByTestId('page-trades')).toBeInTheDocument();
    expect(screen.queryByTestId('alert-toast-crit-1')).not.toBeInTheDocument();

    // A critical alert arrives; AppShell consumes the new hook state and
    // the toast surface appears regardless of which page is active.
    mockState.alerts = [makeAlert()];
    rerender(
      <MemoryRouter initialEntries={['/trades']}>
        <CaptureNavigate />
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<div data-testid="page-dashboard">Dashboard</div>} />
            <Route
              path="trades"
              element={<div data-testid="page-trades">TradeLog</div>}
            />
            <Route
              path="performance"
              element={<div data-testid="page-performance">Performance</div>}
            />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId('alert-toast-crit-1')).toBeInTheDocument();
    expect(screen.getByTestId('page-trades')).toBeInTheDocument();
  });

  it('AlertBanner clears when the active critical-alert list becomes empty (ack/auto-resolve from any page)', () => {
    mockState.alerts = [makeAlert()];
    const { rerender } = renderAppWithRoutes('/trades');
    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Simulate WS push that drops the alert (acknowledged or
    // auto-resolved) — the hook surfaces an empty active-critical list,
    // and the banner unmounts on the next render regardless of route.
    mockState.alerts = [];
    rerender(
      <MemoryRouter initialEntries={['/trades']}>
        <CaptureNavigate />
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<div data-testid="page-dashboard">Dashboard</div>} />
            <Route
              path="trades"
              element={<div data-testid="page-trades">TradeLog</div>}
            />
            <Route
              path="performance"
              element={<div data-testid="page-performance">Performance</div>}
            />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
