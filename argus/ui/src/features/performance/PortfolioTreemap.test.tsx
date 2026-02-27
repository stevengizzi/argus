/**
 * PortfolioTreemap component tests.
 *
 * Sprint 21d Session 8: Portfolio treemap showing position allocations.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PortfolioTreemap } from './PortfolioTreemap';

// Mock the usePositions hook
vi.mock('../../hooks/usePositions', () => ({
  usePositions: vi.fn(),
}));

// Mock the useAccount hook
vi.mock('../../hooks/useAccount', () => ({
  useAccount: vi.fn(),
}));

// Mock the symbolDetailUI store
vi.mock('../../stores/symbolDetailUI', () => ({
  useSymbolDetailUI: () => ({
    open: vi.fn(),
  }),
}));

// Mock ResizeObserver as a class
let mockContainerWidth = 500;

class MockResizeObserver {
  private callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }

  observe(element: Element) {
    this.callback(
      [
        {
          target: element,
          contentRect: { width: mockContainerWidth, height: mockContainerWidth * 0.5 } as DOMRectReadOnly,
          borderBoxSize: [],
          contentBoxSize: [],
          devicePixelContentBoxSize: [],
        },
      ],
      this as unknown as ResizeObserver
    );
  }

  unobserve() {}
  disconnect() {}
}

global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

import { usePositions } from '../../hooks/usePositions';
import { useAccount } from '../../hooks/useAccount';

const mockPositionsData = {
  positions: [
    {
      position_id: 'pos-1',
      strategy_id: 'strat_orb_breakout',
      symbol: 'AAPL',
      side: 'long',
      entry_price: 180.0,
      stop_price: 178.0,
      shares_remaining: 50,
      shares_total: 50,
      current_price: 185.0,
      unrealized_pnl: 250,
      unrealized_pnl_pct: 2.78,
      entry_time: '2026-02-28T10:00:00Z',
      t1_price: 182.0,
      t2_price: 184.0,
      t1_filled: false,
      hold_duration_seconds: 3600,
      r_multiple_current: 2.5,
    },
    {
      position_id: 'pos-2',
      strategy_id: 'strat_vwap_reclaim',
      symbol: 'NVDA',
      side: 'long',
      entry_price: 850.0,
      stop_price: 845.0,
      shares_remaining: 10,
      shares_total: 10,
      current_price: 848.0,
      unrealized_pnl: -20,
      unrealized_pnl_pct: -0.24,
      entry_time: '2026-02-28T11:00:00Z',
      t1_price: 855.0,
      t2_price: 860.0,
      t1_filled: false,
      hold_duration_seconds: 1800,
      r_multiple_current: -0.4,
    },
  ],
  count: 2,
  timestamp: '2026-02-28T12:00:00Z',
};

const mockAccountData = {
  equity: 100000,
  cash: 50000,
  buying_power: 75000,
  daily_pnl: 500,
  daily_pnl_pct: 0.5,
  open_positions_count: 2,
  daily_trades_count: 5,
  market_status: 'open' as const,
  broker_source: 'alpaca',
  data_source: 'alpaca',
  timestamp: '2026-02-28T12:00:00Z',
};

describe('PortfolioTreemap', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders treemap rectangles for positions', () => {
    vi.mocked(usePositions).mockReturnValue({
      data: mockPositionsData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof usePositions>);

    vi.mocked(useAccount).mockReturnValue({
      data: mockAccountData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useAccount>);

    render(<PortfolioTreemap />);

    // Should show the title
    expect(screen.getByText('Portfolio Treemap')).toBeInTheDocument();

    // Should show the description
    expect(
      screen.getByText('Position sizes by capital allocation, colored by P&L %')
    ).toBeInTheDocument();

    // Should render SVG
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Should have rectangles (one per position)
    const rects = svg?.querySelectorAll('rect');
    expect(rects?.length).toBeGreaterThanOrEqual(2);

    // Should show color legend
    expect(screen.getByText('Loss')).toBeInTheDocument();
    expect(screen.getByText('Profit')).toBeInTheDocument();
  });

  it('shows empty state when no positions', () => {
    vi.mocked(usePositions).mockReturnValue({
      data: { positions: [], count: 0, timestamp: '' },
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof usePositions>);

    vi.mocked(useAccount).mockReturnValue({
      data: mockAccountData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useAccount>);

    render(<PortfolioTreemap />);

    expect(screen.getByText('No open positions')).toBeInTheDocument();
  });

  it('shows mobile list fallback on narrow containers', () => {
    // Set narrow container width for mobile fallback
    mockContainerWidth = 350;

    vi.mocked(usePositions).mockReturnValue({
      data: mockPositionsData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof usePositions>);

    vi.mocked(useAccount).mockReturnValue({
      data: mockAccountData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useAccount>);

    render(<PortfolioTreemap />);

    // Mobile fallback should render buttons instead of SVG treemap
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThanOrEqual(2);

    // Reset width for other tests
    mockContainerWidth = 500;
  });

  it('shows loading state', () => {
    vi.mocked(usePositions).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isFetching: true,
    } as ReturnType<typeof usePositions>);

    vi.mocked(useAccount).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isFetching: true,
    } as ReturnType<typeof useAccount>);

    render(<PortfolioTreemap />);

    expect(screen.getByText('Loading positions...')).toBeInTheDocument();
  });
});
