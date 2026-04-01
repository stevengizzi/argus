/**
 * Tests for TradesPage — Sprint 25.6 Session 3 (DEF-067/068/069/073).
 *
 * Verifies: no pagination, metrics from full dataset, filter persistence, sortable columns.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TradeTable, type SortState } from '../features/trades/TradeTable';
import { TradeStatsBar } from '../features/trades/TradeStatsBar';
import { useTrades } from '../hooks/useTrades';
import type { Trade, TradeStatsResponse } from '../api/types';

// Mock Zustand store
vi.mock('../stores/symbolDetailUI', () => ({
  useSymbolDetailUI: () => vi.fn(),
}));

// Mocks for TradesPage render (limit=1000 test)
vi.mock('../hooks/useTrades', () => ({
  useTrades: vi.fn(() => ({
    data: { trades: [], total_count: 0 },
    isLoading: false,
    error: null,
    isFetching: false,
  })),
}));

vi.mock('../hooks/useTradeStats', () => ({
  useTradeStats: vi.fn(() => ({ data: null, isLoading: false })),
}));

vi.mock('../hooks/useCopilotContext', () => ({
  useCopilotContext: vi.fn(),
}));

vi.mock('../features/trades', () => ({
  TradeFilters: () => null,
  TradeStatsBar: () => null,
  TradeTable: () => null,
  TradeDetailPanel: () => null,
  TradeStatsBarSkeleton: () => null,
  TradeTableSkeleton: () => null,
}));

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client');
  return { ...actual, getToken: vi.fn(() => null) };
});

function makeTrade(overrides: Partial<Trade> = {}): Trade {
  return {
    id: `trade-${Math.random().toString(36).slice(2, 8)}`,
    strategy_id: 'orb_breakout',
    symbol: 'AAPL',
    side: 'long',
    entry_price: 150.0,
    entry_time: '2026-03-19T10:15:00Z',
    exit_price: 153.0,
    exit_time: '2026-03-19T11:30:00Z',
    shares: 100,
    pnl_dollars: 300.0,
    pnl_r_multiple: 1.5,
    exit_reason: 'target_1',
    hold_duration_seconds: 4500,
    commission: 1.0,
    market_regime: 'bullish',
    stop_price: 148.0,
    target_prices: [153.0, 156.0],
    quality_grade: null,
    quality_score: null,
    ...overrides,
  };
}

describe('TradesPage — DEF-067: no pagination controls', () => {
  it('renders table without pagination buttons', () => {
    const trades = Array.from({ length: 25 }, (_, i) =>
      makeTrade({ id: `t-${i}`, symbol: `SYM${i}` })
    );

    render(
      <TradeTable trades={trades} totalCount={25} />
    );

    // No "Prev" / "Next" buttons
    expect(screen.queryByText('Prev')).not.toBeInTheDocument();
    expect(screen.queryByText('Next')).not.toBeInTheDocument();
    // No "Page X of Y" text
    expect(screen.queryByText(/^Page \d+ of \d+$/)).not.toBeInTheDocument();
    // Scrollable container present
    expect(screen.getByTestId('trade-table-scroll')).toBeInTheDocument();
    // All 25 rows rendered (no pagination slicing)
    const rows = screen.getAllByRole('row');
    // 1 header row + 25 data rows
    expect(rows.length).toBe(26);
  });
});

describe('TradesPage — DEF-068: metrics from server-side stats', () => {
  it('renders server-side stats (win rate, net P&L, avg R)', () => {
    const stats: TradeStatsResponse = {
      total_trades: 3,
      wins: 2,
      losses: 1,
      win_rate: 0.6667,
      net_pnl: 400.0,
      avg_r: 0.85,
      timestamp: new Date().toISOString(),
    };

    render(
      <TradeStatsBar stats={stats} />
    );

    // Win rate from server (0.6667 × 100 = 66.67%)
    expect(screen.getByText('66.67%')).toBeInTheDocument();
    // Net P&L from server
    expect(screen.getByText('$400.00')).toBeInTheDocument();
    // Trade count from server
    expect(screen.getByText('3')).toBeInTheDocument();
    // Avg R from server
    expect(screen.getByText('+0.85R')).toBeInTheDocument();
  });
});

describe('TradesPage — DEF-069: time filter persistence', () => {
  it('Zustand store quickFilter drives date params via computeDateRangeForQuickFilter', async () => {
    // This tests the store function directly — the integration is in TradesPage
    const { computeDateRangeForQuickFilter, useTradeFiltersStore } = await import(
      '../stores/tradeFilters'
    );

    // Set store to 'today'
    useTradeFiltersStore.getState().setQuickFilter('today');

    const state = useTradeFiltersStore.getState();
    expect(state.quickFilter).toBe('today');

    // Verify computeDateRangeForQuickFilter produces matching dates
    const { dateFrom, dateTo } = computeDateRangeForQuickFilter('today');
    expect(state.dateFrom).toBe(dateFrom);
    expect(state.dateTo).toBe(dateTo);

    // Reset
    useTradeFiltersStore.getState().setQuickFilter('all');
    const resetState = useTradeFiltersStore.getState();
    expect(resetState.dateFrom).toBeUndefined();
    expect(resetState.dateTo).toBeUndefined();
  });
});

describe('TradesPage — DEF-073: sortable columns', () => {
  it('clicking P&L header sorts trades by P&L', () => {
    const trades = [
      makeTrade({ id: 't1', pnl_dollars: -200, symbol: 'LOSS' }),
      makeTrade({ id: 't2', pnl_dollars: 500, symbol: 'WIN' }),
      makeTrade({ id: 't3', pnl_dollars: 100, symbol: 'SMALL' }),
    ];

    render(
      <TradeTable trades={trades} totalCount={3} />
    );

    // Before sort — original order
    const getCellTexts = () => {
      const rows = screen.getAllByRole('row').slice(1); // skip header
      return rows.map((row) => row.querySelector('td')?.textContent ?? '');
    };

    // Click P&L header → ascending sort
    const pnlHeader = screen.getByTestId('sort-pnl');
    fireEvent.click(pnlHeader);

    // After ascending sort, first row should have lowest P&L (-200)
    const rowsAsc = screen.getAllByRole('row').slice(1);
    // The P&L column is the 8th column (index 7 in desktop), but in phone view
    // it's rendered differently. Check via text content in the P&L cells.
    const pnlCells = rowsAsc.map((row) => {
      const cells = row.querySelectorAll('td');
      // The P&L cell — in phone view the first visible td after the combined column
      // Use the cell that contains dollar amounts
      return Array.from(cells).find((c) => c.textContent?.includes('$'))?.textContent ?? '';
    });
    // First should be -$200, last should be $500
    expect(pnlCells[0]).toContain('200');
    expect(pnlCells[2]).toContain('500');

    // Click again → descending
    fireEvent.click(pnlHeader);
    const rowsDesc = screen.getAllByRole('row').slice(1);
    const pnlCellsDesc = rowsDesc.map((row) =>
      Array.from(row.querySelectorAll('td')).find((c) => c.textContent?.includes('$'))?.textContent ?? ''
    );
    // First should be $500, last should be -$200
    expect(pnlCellsDesc[0]).toContain('500');
    expect(pnlCellsDesc[2]).toContain('200');

    // Click again → clear sort (back to original order)
    fireEvent.click(pnlHeader);
    // Sort indicator should be gone
    expect(pnlHeader.querySelector('svg')).toBeNull();
  });
});

describe('TradesPage — trades limit set to 1000', () => {
  it('passes limit=1000 to useTrades', async () => {
    const { TradesPage } = await import('../pages/TradesPage');
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <TradesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(vi.mocked(useTrades)).toHaveBeenCalledWith(
      expect.objectContaining({ limit: 1000 }),
    );
  });
});
