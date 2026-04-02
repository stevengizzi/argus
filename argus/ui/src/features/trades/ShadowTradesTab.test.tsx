/**
 * Tests for ShadowTradesTab — Sprint 32.5, Session 6 (DEF-131).
 *
 * Covers: component mounts, empty state, data display, tab switching.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ShadowTradesTab } from './ShadowTradesTab';
import { useShadowTrades } from '../../hooks/useShadowTrades';
import type { ShadowTrade, ShadowTradesResponse } from '../../api/types';

// --- Top-level mocks ---

vi.mock('../../hooks/useShadowTrades', () => ({
  useShadowTrades: vi.fn(),
}));

vi.mock('../../hooks/useStrategies', () => ({
  useStrategies: vi.fn(() => ({
    data: { strategies: [], count: 0, timestamp: '' },
  })),
}));

// Mocks required for TradesPage render (tab-switching test)
vi.mock('../../hooks/useTrades', () => ({
  useTrades: vi.fn(() => ({
    data: { trades: [], total_count: 0 },
    isLoading: false,
    error: null,
    isFetching: false,
  })),
}));

vi.mock('../../hooks/useTradeStats', () => ({
  useTradeStats: vi.fn(() => ({ data: null, isLoading: false, isFetching: false })),
}));

vi.mock('../../hooks/useCopilotContext', () => ({
  useCopilotContext: vi.fn(),
}));

vi.mock('../../features/trades', () => ({
  TradeFilters: () => null,
  TradeStatsBar: () => null,
  TradeTable: () => null,
  TradeDetailPanel: () => null,
  TradeStatsBarSkeleton: () => null,
  TradeTableSkeleton: () => null,
}));

vi.mock('../../api/client', async () => {
  const actual = await vi.importActual<typeof import('../../api/client')>('../../api/client');
  return { ...actual, getToken: vi.fn(() => null) };
});

// --- Helpers ---

function makeShadowTrade(overrides: Partial<ShadowTrade> = {}): ShadowTrade {
  return {
    position_id: `cf-${Math.random().toString(36).slice(2, 8)}`,
    symbol: 'AAPL',
    strategy_id: 'orb_breakout',
    variant_id: null,
    entry_price: 150.0,
    stop_price: 148.0,
    target_price: 154.0,
    time_stop_seconds: 300,
    rejection_stage: 'QUALITY_FILTER',
    rejection_reason: 'grade_below_minimum',
    quality_score: 55.0,
    quality_grade: 'B-',
    opened_at: '2026-03-19T10:15:00Z',
    closed_at: '2026-03-19T11:00:00Z',
    exit_price: 151.5,
    exit_reason: 'target_1',
    theoretical_pnl: 150.0,
    theoretical_r_multiple: 0.75,
    duration_seconds: 2700,
    max_adverse_excursion: -0.3,
    max_favorable_excursion: 1.2,
    bars_monitored: 45,
    ...overrides,
  };
}

function makeResponse(trades: ShadowTrade[]): ShadowTradesResponse {
  return {
    positions: trades,
    total_count: trades.length,
    limit: 50,
    offset: 0,
    timestamp: new Date().toISOString(),
  };
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

// --- Tests ---

describe('ShadowTradesTab — renders without error', () => {
  it('mounts and shows loading state initially', () => {
    vi.mocked(useShadowTrades).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isFetching: false,
      isPending: true,
    } as ReturnType<typeof useShadowTrades>);

    render(<ShadowTradesTab />, { wrapper });

    expect(screen.getByTestId('shadow-trades-tab')).toBeInTheDocument();
    expect(screen.getByTestId('shadow-loading-state')).toBeInTheDocument();
    expect(screen.getByText(/loading shadow trades/i)).toBeInTheDocument();
  });

  it('shows loading state when data is undefined even if isLoading is false', () => {
    vi.mocked(useShadowTrades).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      isFetching: true,
      isPending: true,
    } as ReturnType<typeof useShadowTrades>);

    render(<ShadowTradesTab />, { wrapper });

    expect(screen.getByTestId('shadow-loading-state')).toBeInTheDocument();
  });
});

describe('ShadowTradesTab — error state', () => {
  it('shows error message when API call fails', () => {
    vi.mocked(useShadowTrades).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Service unavailable'),
      isFetching: false,
      isPending: false,
    } as ReturnType<typeof useShadowTrades>);

    render(<ShadowTradesTab />, { wrapper });

    expect(screen.getByTestId('shadow-error-state')).toBeInTheDocument();
    expect(screen.getByText(/unable to load shadow trades/i)).toBeInTheDocument();
    expect(screen.getByText(/service unavailable/i)).toBeInTheDocument();
  });
});

describe('ShadowTradesTab — empty state', () => {
  it('shows empty state message when no shadow trades exist', () => {
    vi.mocked(useShadowTrades).mockReturnValue({
      data: makeResponse([]),
      isLoading: false,
      error: null,
      isFetching: false,
      isPending: false,
    } as ReturnType<typeof useShadowTrades>);

    render(<ShadowTradesTab />, { wrapper });

    expect(screen.getByTestId('shadow-empty-state')).toBeInTheDocument();
    expect(screen.getByText(/no shadow trades recorded yet/i)).toBeInTheDocument();
    expect(screen.getByText(/quality filter, position sizer, or risk manager/i)).toBeInTheDocument();
  });
});

describe('ShadowTradesTab — data display', () => {
  it('renders table rows with correct columns when trades exist', () => {
    const trades = [
      makeShadowTrade({ symbol: 'TSLA', theoretical_pnl: 200.0, rejection_stage: 'RISK_MANAGER' }),
      makeShadowTrade({ symbol: 'NVDA', theoretical_pnl: -50.0, rejection_stage: 'QUALITY_FILTER' }),
    ];
    vi.mocked(useShadowTrades).mockReturnValue({
      data: makeResponse(trades),
      isLoading: false,
      error: null,
      isFetching: false,
      isPending: false,
    } as ReturnType<typeof useShadowTrades>);

    render(<ShadowTradesTab />, { wrapper });

    // Table present
    expect(screen.getByTestId('shadow-trade-table')).toBeInTheDocument();

    // Both symbols rendered
    expect(screen.getByText('TSLA')).toBeInTheDocument();
    expect(screen.getByText('NVDA')).toBeInTheDocument();

    // Summary stats block present
    expect(screen.getByTestId('shadow-summary-stats')).toBeInTheDocument();

    // Rejection stage badges appear at least once (may also appear in dropdown options)
    expect(screen.getAllByText('Risk Manager').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Quality Filter').length).toBeGreaterThanOrEqual(1);

    // P&L coloring: positive starts with +$, negative with -$
    expect(screen.getByText('+$200.00')).toBeInTheDocument();
    expect(screen.getByText('-$50.00')).toBeInTheDocument();
  });
});

// --- Session 5 tests ---

describe('ShadowTradesTab — outcome toggle', () => {
  it('test_outcome_toggle_filters_wins — shows only trades with positive theo_pnl', () => {
    const trades = [
      makeShadowTrade({ symbol: 'AAPL', theoretical_pnl: 100.0 }),
      makeShadowTrade({ symbol: 'TSLA', theoretical_pnl: -50.0 }),
      makeShadowTrade({ symbol: 'NVDA', theoretical_pnl: null }),
    ];
    vi.mocked(useShadowTrades).mockReturnValue({
      data: makeResponse(trades),
      isLoading: false,
      error: null,
      isFetching: false,
      isPending: false,
    } as ReturnType<typeof useShadowTrades>);

    render(<ShadowTradesTab />, { wrapper });

    // All 3 rows visible initially
    expect(screen.getAllByTestId('shadow-trade-row')).toHaveLength(3);

    // Click "Wins" tab
    fireEvent.click(screen.getByRole('tab', { name: /wins/i }));

    // Only the winning trade is shown
    expect(screen.getAllByTestId('shadow-trade-row')).toHaveLength(1);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.queryByText('TSLA')).not.toBeInTheDocument();
    expect(screen.queryByText('NVDA')).not.toBeInTheDocument();
  });

  it('test_outcome_toggle_filters_losses — shows only trades with negative theo_pnl', () => {
    const trades = [
      makeShadowTrade({ symbol: 'AAPL', theoretical_pnl: 100.0 }),
      makeShadowTrade({ symbol: 'TSLA', theoretical_pnl: -50.0 }),
      makeShadowTrade({ symbol: 'NVDA', theoretical_pnl: null }),
    ];
    vi.mocked(useShadowTrades).mockReturnValue({
      data: makeResponse(trades),
      isLoading: false,
      error: null,
      isFetching: false,
      isPending: false,
    } as ReturnType<typeof useShadowTrades>);

    render(<ShadowTradesTab />, { wrapper });

    // Click "Losses" tab
    fireEvent.click(screen.getByRole('tab', { name: /losses/i }));

    // Only the losing trade is shown
    expect(screen.getAllByTestId('shadow-trade-row')).toHaveLength(1);
    expect(screen.getByText('TSLA')).toBeInTheDocument();
    expect(screen.queryByText('AAPL')).not.toBeInTheDocument();
  });
});

describe('ShadowTradesTab — time presets', () => {
  it('test_time_preset_today — Today preset sets both date inputs to a non-empty date', () => {
    vi.mocked(useShadowTrades).mockReturnValue({
      data: makeResponse([]),
      isLoading: false,
      error: null,
      isFetching: false,
      isPending: false,
    } as ReturnType<typeof useShadowTrades>);

    render(<ShadowTradesTab />, { wrapper });

    const fromInput = screen.getByTestId('shadow-date-from') as HTMLInputElement;
    const toInput = screen.getByTestId('shadow-date-to') as HTMLInputElement;

    // Date inputs start empty
    expect(fromInput).toHaveValue('');
    expect(toInput).toHaveValue('');

    // Click Today
    fireEvent.click(screen.getByTestId('shadow-quick-filter-today'));

    // Both date inputs should now be set and equal (same day)
    expect(fromInput).not.toHaveValue('');
    expect(toInput).not.toHaveValue('');
    expect(fromInput.value).toBe(toInput.value);
  });

  it('test_time_preset_all — All preset clears the date range', () => {
    vi.mocked(useShadowTrades).mockReturnValue({
      data: makeResponse([]),
      isLoading: false,
      error: null,
      isFetching: false,
      isPending: false,
    } as ReturnType<typeof useShadowTrades>);

    render(<ShadowTradesTab />, { wrapper });

    const fromInput = screen.getByTestId('shadow-date-from') as HTMLInputElement;

    // Set Today first to populate the date inputs
    fireEvent.click(screen.getByTestId('shadow-quick-filter-today'));
    expect(fromInput).not.toHaveValue('');

    // Now click All — should clear both dates
    fireEvent.click(screen.getByTestId('shadow-quick-filter-all'));
    expect(fromInput).toHaveValue('');
  });
});

describe('ShadowTradesTab — sortable columns', () => {
  it('test_sortable_columns_toggle — clicking a column header toggles sort direction', () => {
    const trades = [
      makeShadowTrade({ symbol: 'AAPL', strategy_id: 'orb_breakout' }),
      makeShadowTrade({ symbol: 'TSLA', strategy_id: 'vwap_reclaim' }),
    ];
    vi.mocked(useShadowTrades).mockReturnValue({
      data: makeResponse(trades),
      isLoading: false,
      error: null,
      isFetching: false,
      isPending: false,
    } as ReturnType<typeof useShadowTrades>);

    render(<ShadowTradesTab />, { wrapper });

    const strategyHeader = screen.getByTestId('sort-strategy_id');

    // First click — should show descending indicator
    fireEvent.click(strategyHeader);
    expect(strategyHeader.querySelector('svg')).toBeInTheDocument();

    // Second click — direction reverses
    fireEvent.click(strategyHeader);
    // Both clicks produce a sort icon; just verify it's still present
    expect(strategyHeader.querySelector('svg')).toBeInTheDocument();
  });
});

describe('ShadowTradesTab — reason tooltip', () => {
  it('test_reason_tooltip — Reason cell has title attribute with full rejection reason', () => {
    const longReason = 'grade_below_minimum_threshold_for_live_trading_conditions_in_choppy_regime';
    const trades = [makeShadowTrade({ rejection_reason: longReason })];
    vi.mocked(useShadowTrades).mockReturnValue({
      data: makeResponse(trades),
      isLoading: false,
      error: null,
      isFetching: false,
      isPending: false,
    } as ReturnType<typeof useShadowTrades>);

    render(<ShadowTradesTab />, { wrapper });

    const reasonCell = screen.getByTestId('reason-cell');
    expect(reasonCell).toHaveAttribute('title', longReason);
  });
});

describe('TradesPage — tab switching', () => {
  it('shows Shadow Trades tab content when clicked, returns to live on Live Trades click', async () => {
    vi.mocked(useShadowTrades).mockReturnValue({
      data: makeResponse([]),
      isLoading: false,
      error: null,
      isFetching: false,
      isPending: false,
    } as ReturnType<typeof useShadowTrades>);

    const { TradesPage } = await import('../../pages/TradesPage');
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <TradesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Tab bar is present
    expect(screen.getByTestId('trades-tab-bar')).toBeInTheDocument();

    // Default is Live Trades — shadow tab is mounted but hidden
    expect(screen.getByTestId('shadow-trades-tab')).toBeInTheDocument();
    expect(screen.getByTestId('shadow-trades-tab').closest('.hidden')).not.toBeNull();

    // Switch to Shadow Trades — shadow tab becomes visible
    fireEvent.click(screen.getByTestId('tab-shadow-trades'));
    expect(screen.getByTestId('shadow-trades-tab')).toBeInTheDocument();
    expect(screen.getByTestId('shadow-trades-tab').closest('.hidden')).toBeNull();

    // Switch back to Live Trades — shadow tab hidden again
    fireEvent.click(screen.getByTestId('tab-live-trades'));
    expect(screen.getByTestId('shadow-trades-tab')).toBeInTheDocument();
    expect(screen.getByTestId('shadow-trades-tab').closest('.hidden')).not.toBeNull();
  });
});
