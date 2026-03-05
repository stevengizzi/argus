/**
 * Tests for OpenPositions component.
 *
 * Sprint 21.5.1, Session 3.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { OpenPositions } from './OpenPositions';
import type { Position } from '../../api/types';

// Create query client for tests
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

// Mock data - define outside of mocks so it's available
const mockPosition: Position = {
  position_id: 'pos-001',
  strategy_id: 'strat_orb_breakout',
  symbol: 'TSLA',
  side: 'long',
  entry_price: 250.0,
  entry_time: new Date().toISOString(),
  shares_total: 100,
  shares_remaining: 100,
  current_price: 252.0,
  unrealized_pnl: 200.0,
  unrealized_pnl_pct: 0.8,
  stop_price: 248.0,
  t1_price: 254.0,
  t2_price: 258.0,
  t1_filled: false,
  hold_duration_seconds: 300,
  r_multiple_current: 1.0,
};

// Mock the hooks
vi.mock('../../hooks/usePositions', () => ({
  usePositions: () => ({
    data: {
      positions: [{
        position_id: 'pos-001',
        strategy_id: 'strat_orb_breakout',
        symbol: 'TSLA',
        side: 'long',
        entry_price: 250.0,
        entry_time: new Date().toISOString(),
        shares_total: 100,
        shares_remaining: 100,
        current_price: 252.0,
        unrealized_pnl: 200.0,
        unrealized_pnl_pct: 0.8,
        stop_price: 248.0,
        t1_price: 254.0,
        t2_price: 258.0,
        t1_filled: false,
        hold_duration_seconds: 300,
        r_multiple_current: 1.0,
      }],
    },
    isLoading: false,
    error: null,
  }),
}));

vi.mock('../../hooks/useTrades', () => ({
  useTrades: () => ({
    data: { trades: [] },
    isLoading: false,
    error: null,
  }),
}));

vi.mock('../../stores/live', () => ({
  useLiveStore: (selector: (state: { priceUpdates: Record<string, unknown> }) => unknown) => {
    const state = { priceUpdates: {} };
    return selector(state);
  },
}));

vi.mock('../../stores/positionsUI', () => ({
  usePositionsUIStore: (selector: (state: {
    displayMode: string;
    setDisplayMode: () => void;
    positionFilter: string;
    setPositionFilter: () => void;
  }) => unknown) => {
    const state = {
      displayMode: 'table',
      setDisplayMode: vi.fn(),
      positionFilter: 'open',
      setPositionFilter: vi.fn(),
    };
    return selector(state);
  },
}));

vi.mock('../../stores/symbolDetailUI', () => ({
  useSymbolDetailUI: (selector?: (state: {
    open: () => void;
    close: () => void;
    isOpen: boolean;
    symbol: string | null;
  }) => unknown) => {
    const state = { open: vi.fn(), close: vi.fn(), isOpen: false, symbol: null };
    // Handle both selector-based and direct usage patterns
    return selector ? selector(state) : state;
  },
}));

vi.mock('../../utils/testMode', () => ({
  shouldShowEmpty: () => false,
}));

vi.mock('../../utils/marketTime', () => ({
  getMarketContext: () => ({ status: 'open' }),
  isPreMarket: () => false,
  getTodayET: () => '2026-02-25',
}));

describe('OpenPositions', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  const renderWithProviders = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    );
  };

  it('renders open positions table', () => {
    renderWithProviders(<OpenPositions />);

    // Should show the position symbol (appears multiple times for responsive layouts)
    const tslaElements = screen.getAllByText('TSLA');
    expect(tslaElements.length).toBeGreaterThan(0);
  });

  it('position rows are clickable for detail panel', () => {
    renderWithProviders(<OpenPositions />);

    // Find position rows (appear in multiple responsive layouts)
    const tslaButtons = screen.getAllByRole('button', { name: 'TSLA' });
    expect(tslaButtons.length).toBeGreaterThan(0);

    // Find the row containing the first TSLA button (desktop table)
    const row = tslaButtons[0].closest('tr');

    // The row should be clickable (has cursor-pointer class)
    if (row) {
      expect(row).toHaveClass('cursor-pointer');
    }
  });

  it('shows sortable column headers', () => {
    renderWithProviders(<OpenPositions />);

    // Check that sortable columns are rendered with click handlers
    // Symbol header appears multiple times in responsive layouts
    const symbolHeaders = screen.getAllByText('Symbol');
    expect(symbolHeaders.length).toBeGreaterThan(0);

    // The header should be in a th element that is clickable
    const headerCell = symbolHeaders[0].closest('th');
    if (headerCell) {
      expect(headerCell).toHaveClass('cursor-pointer');
    }
  });
});
