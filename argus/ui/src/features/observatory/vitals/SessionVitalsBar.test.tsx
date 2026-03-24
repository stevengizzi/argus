/**
 * Tests for SessionVitalsBar, DebriefDatePicker, useDebriefMode, and useSessionVitals.
 *
 * Sprint 25, Session 9.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionVitalsBar } from './SessionVitalsBar';
import { DebriefDatePicker } from './DebriefDatePicker';
import { useDebriefMode } from '../hooks/useDebriefMode';
import { useSessionVitals } from '../hooks/useSessionVitals';
import type { UseSessionVitalsResult } from '../hooks/useSessionVitals';
import type { UseDebriefModeResult, DebriefDate } from '../hooks/useDebriefMode';

// Mock the API client
vi.mock('../../../api/client', () => ({
  getToken: () => 'mock-token',
  getObservatorySessionSummary: vi.fn().mockResolvedValue({
    total_evaluations: 150,
    total_signals: 5,
    total_trades: 2,
    symbols_evaluated: 42,
    top_blockers: [{ condition_name: 'volume_ratio', rejection_count: 64, percentage: 43 }],
    closest_miss: {
      symbol: 'SMCI',
      strategy: 'AfMo',
      conditions_passed: 6,
      conditions_total: 8,
    },
    date: '2026-03-17',
    timestamp: '2026-03-17T14:30:00Z',
  }),
}));

function createQueryWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function mockVitals(overrides: Partial<UseSessionVitalsResult> = {}): UseSessionVitalsResult {
  return {
    metrics: {
      symbolsReceiving: 42,
      totalEvaluations: 150,
      totalSignals: 5,
      totalTrades: 2,
    },
    connectionStatus: { databento: true, ibkr: true, ws: true },
    closestMiss: { symbol: 'SMCI', strategy: 'AfMo', conditions_passed: 6, conditions_total: 8 },
    topBlocker: { condition_name: 'volume_ratio', rejection_count: 64, percentage: 43 },
    regimeVector: null,
    marketTime: '10:47 AM ET',
    isLive: true,
    ...overrides,
  };
}

function mockDebrief(overrides: Partial<UseDebriefModeResult> = {}): UseDebriefModeResult {
  return {
    isDebrief: false,
    selectedDate: null,
    enterDebrief: vi.fn(),
    exitDebrief: vi.fn(),
    availableDates: [
      { date: '2026-03-16', label: 'Mon Mar 16', isWeekend: false },
      { date: '2026-03-15', label: 'Sun Mar 15', isWeekend: true },
      { date: '2026-03-14', label: 'Sat Mar 14', isWeekend: true },
      { date: '2026-03-13', label: 'Thu Mar 13', isWeekend: false },
      { date: '2026-03-12', label: 'Wed Mar 12', isWeekend: false },
      { date: '2026-03-11', label: 'Tue Mar 11', isWeekend: false },
      { date: '2026-03-10', label: 'Mon Mar 10', isWeekend: false },
    ],
    validationError: null,
    ...overrides,
  };
}

describe('SessionVitalsBar', () => {
  it('renders all three sections with metrics', () => {
    render(
      <SessionVitalsBar
        currentView="matrix"
        onChangeView={vi.fn()}
        vitals={mockVitals()}
        debrief={mockDebrief()}
      />,
    );

    expect(screen.getByTestId('session-vitals-bar')).toBeInTheDocument();
    expect(screen.getByTestId('view-tabs')).toBeInTheDocument();
    expect(screen.getByTestId('session-metrics')).toBeInTheDocument();
    expect(screen.getByTestId('diagnostics-section')).toBeInTheDocument();
  });

  it('displays connection status dots', () => {
    render(
      <SessionVitalsBar
        currentView="matrix"
        onChangeView={vi.fn()}
        vitals={mockVitals()}
        debrief={mockDebrief()}
      />,
    );

    expect(screen.getByTestId('connection-dot-databento')).toBeInTheDocument();
    expect(screen.getByTestId('connection-dot-ibkr')).toBeInTheDocument();
  });

  it('updates metrics from vitals data', () => {
    render(
      <SessionVitalsBar
        currentView="matrix"
        onChangeView={vi.fn()}
        vitals={mockVitals({ metrics: {
          symbolsReceiving: 99,
          totalEvaluations: 500,
          totalSignals: 12,
          totalTrades: 4,
        } })}
        debrief={mockDebrief()}
      />,
    );

    expect(screen.getByTestId('metric-evaluations')).toHaveTextContent('500');
    expect(screen.getByTestId('metric-signals')).toHaveTextContent('12');
    expect(screen.getByTestId('metric-trades')).toHaveTextContent('4');
    expect(screen.getByTestId('metric-symbols')).toHaveTextContent('99');
  });

  it('shows closest miss and top blocker', () => {
    render(
      <SessionVitalsBar
        currentView="matrix"
        onChangeView={vi.fn()}
        vitals={mockVitals()}
        debrief={mockDebrief()}
      />,
    );

    expect(screen.getByTestId('closest-miss')).toHaveTextContent('SMCI');
    expect(screen.getByTestId('closest-miss')).toHaveTextContent('6/8');
    expect(screen.getByTestId('top-blocker')).toHaveTextContent('volume_ratio');
    expect(screen.getByTestId('top-blocker')).toHaveTextContent('43%');
  });

  it('hides connection dots in debrief mode', () => {
    render(
      <SessionVitalsBar
        currentView="matrix"
        onChangeView={vi.fn()}
        vitals={mockVitals({ isLive: false, marketTime: 'Reviewing 2026-03-16' })}
        debrief={mockDebrief({ isDebrief: true, selectedDate: '2026-03-16' })}
      />,
    );

    expect(screen.queryByTestId('connection-dot-databento')).not.toBeInTheDocument();
    expect(screen.getByTestId('debrief-indicator')).toHaveTextContent('Reviewing 2026-03-16');
  });
});

describe('DebriefDatePicker', () => {
  it('shows last 7 days when opened', () => {
    const dates: DebriefDate[] = [
      { date: '2026-03-16', label: 'Mon Mar 16', isWeekend: false },
      { date: '2026-03-15', label: 'Sun Mar 15', isWeekend: true },
      { date: '2026-03-14', label: 'Sat Mar 14', isWeekend: true },
      { date: '2026-03-13', label: 'Thu Mar 13', isWeekend: false },
      { date: '2026-03-12', label: 'Wed Mar 12', isWeekend: false },
      { date: '2026-03-11', label: 'Tue Mar 11', isWeekend: false },
      { date: '2026-03-10', label: 'Mon Mar 10', isWeekend: false },
    ];

    render(
      <DebriefDatePicker
        isDebrief={false}
        selectedDate={null}
        availableDates={dates}
        validationError={null}
        onSelectDate={vi.fn()}
        onExitDebrief={vi.fn()}
      />,
    );

    // Click to open
    fireEvent.click(screen.getByTestId('debrief-toggle-button'));

    const dateList = screen.getByTestId('debrief-date-list');
    expect(dateList).toBeInTheDocument();

    // All 7 dates visible
    expect(screen.getByTestId('debrief-date-2026-03-16')).toBeInTheDocument();
    expect(screen.getByTestId('debrief-date-2026-03-10')).toBeInTheDocument();

    // Weekend dates are disabled
    expect(screen.getByTestId('debrief-date-2026-03-15')).toBeDisabled();
    expect(screen.getByTestId('debrief-date-2026-03-14')).toBeDisabled();

    // Weekday dates are enabled
    expect(screen.getByTestId('debrief-date-2026-03-16')).not.toBeDisabled();
  });

  it('calls onExitDebrief when Live button clicked in debrief mode', () => {
    const onExit = vi.fn();
    render(
      <DebriefDatePicker
        isDebrief={true}
        selectedDate="2026-03-16"
        availableDates={[]}
        validationError={null}
        onSelectDate={vi.fn()}
        onExitDebrief={onExit}
      />,
    );

    fireEvent.click(screen.getByTestId('debrief-live-button'));
    expect(onExit).toHaveBeenCalledOnce();
  });
});

describe('useDebriefMode', () => {
  it('validates dates within retention window and rejects weekends', () => {
    const { result } = renderHook(() => useDebriefMode());

    // Should have 7 available dates
    expect(result.current.availableDates).toHaveLength(7);

    // Start in live mode
    expect(result.current.isDebrief).toBe(false);
    expect(result.current.selectedDate).toBeNull();

    // Enter debrief with a weekend date — should set validation error
    const weekendDate = result.current.availableDates.find((d) => d.isWeekend);
    if (weekendDate) {
      act(() => result.current.enterDebrief(weekendDate.date));
      expect(result.current.isDebrief).toBe(false);
      expect(result.current.validationError).toContain('No market data');
    }

    // Enter debrief with a weekday date — should succeed
    const weekdayDate = result.current.availableDates.find((d) => !d.isWeekend);
    if (weekdayDate) {
      act(() => result.current.enterDebrief(weekdayDate.date));
      expect(result.current.isDebrief).toBe(true);
      expect(result.current.selectedDate).toBe(weekdayDate.date);
      expect(result.current.validationError).toBeNull();
    }
  });

  it('exits debrief and returns to live mode', () => {
    const { result } = renderHook(() => useDebriefMode());

    const weekdayDate = result.current.availableDates.find((d) => !d.isWeekend);
    if (weekdayDate) {
      act(() => result.current.enterDebrief(weekdayDate.date));
      expect(result.current.isDebrief).toBe(true);

      act(() => result.current.exitDebrief());
      expect(result.current.isDebrief).toBe(false);
      expect(result.current.selectedDate).toBeNull();
    }
  });

  it('rejects dates outside the retention window', () => {
    const { result } = renderHook(() => useDebriefMode());
    act(() => result.current.enterDebrief('2020-01-01'));
    expect(result.current.isDebrief).toBe(false);
    expect(result.current.validationError).toContain('outside');
  });
});

describe('useSessionVitals', () => {
  it('returns debrief market time when date is provided', async () => {
    const { result } = renderHook(
      () => useSessionVitals({ date: '2026-03-16' }),
      { wrapper: createQueryWrapper() },
    );

    expect(result.current.isLive).toBe(false);
    expect(result.current.marketTime).toBe('Reviewing 2026-03-16');
  });

  it('returns live market time when no date', async () => {
    const { result } = renderHook(
      () => useSessionVitals({}),
      { wrapper: createQueryWrapper() },
    );

    expect(result.current.isLive).toBe(true);
    expect(result.current.marketTime).toContain('ET');
    expect(result.current.marketTime).not.toContain('Reviewing');
  });
});
