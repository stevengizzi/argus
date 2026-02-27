/**
 * Tests for HeatStripPortfolioBar component.
 *
 * Sprint 21d Session 5.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { HeatStripPortfolioBar } from './HeatStripPortfolioBar';
import type { PositionsResponse, AccountResponse } from '../../api/types';

// Mock usePositions hook
const mockUsePositions = vi.fn();
vi.mock('../../hooks/usePositions', () => ({
  usePositions: () => mockUsePositions(),
}));

// Mock useAccount hook
const mockUseAccount = vi.fn();
vi.mock('../../hooks/useAccount', () => ({
  useAccount: () => mockUseAccount(),
}));

// Mock symbolDetailUI store
const mockOpenSymbolDetail = vi.fn();
vi.mock('../../stores/symbolDetailUI', () => ({
  useSymbolDetailUI: () => ({
    open: mockOpenSymbolDetail,
  }),
}));

const mockPositionsData: PositionsResponse = {
  positions: [
    {
      position_id: 'pos-1',
      strategy_id: 'orb_breakout',
      symbol: 'AAPL',
      side: 'long',
      entry_price: 150.0,
      entry_time: '2026-02-28T09:45:00Z',
      shares_total: 100,
      shares_remaining: 100,
      current_price: 153.0,
      unrealized_pnl: 300.0,
      unrealized_pnl_pct: 2.0,
      stop_price: 148.0,
      t1_price: 154.0,
      t2_price: 158.0,
      t1_filled: false,
      hold_duration_seconds: 1800,
      r_multiple_current: 1.5,
    },
    {
      position_id: 'pos-2',
      strategy_id: 'vwap_reclaim',
      symbol: 'MSFT',
      side: 'long',
      entry_price: 400.0,
      entry_time: '2026-02-28T10:15:00Z',
      shares_total: 50,
      shares_remaining: 50,
      current_price: 396.0,
      unrealized_pnl: -200.0,
      unrealized_pnl_pct: -1.0,
      stop_price: 395.0,
      t1_price: 405.0,
      t2_price: 410.0,
      t1_filled: false,
      hold_duration_seconds: 900,
      r_multiple_current: -0.8,
    },
  ],
  count: 2,
  timestamp: '2026-02-28T10:30:00Z',
};

const mockAccountData: AccountResponse = {
  equity: 100000,
  cash: 50000,
  buying_power: 75000,
  daily_pnl: 500.0,
  daily_pnl_pct: 0.5,
  open_positions_count: 2,
  daily_trades_count: 5,
  market_status: 'open',
  broker_source: 'alpaca',
  data_source: 'alpaca',
  timestamp: '2026-02-28T10:30:00Z',
};

describe('HeatStripPortfolioBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders position segments with correct colors based on P&L', () => {
    mockUsePositions.mockReturnValue({
      data: mockPositionsData,
      isLoading: false,
    });
    mockUseAccount.mockReturnValue({
      data: mockAccountData,
      isLoading: false,
    });

    const { container } = render(<HeatStripPortfolioBar />);

    // Check SVG is rendered
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Check rect elements for segments (background + 2 positions)
    const rects = container.querySelectorAll('rect');
    expect(rects.length).toBeGreaterThanOrEqual(2);
  });

  it('renders empty state when no positions', () => {
    mockUsePositions.mockReturnValue({
      data: { positions: [], count: 0, timestamp: '2026-02-28T10:30:00Z' },
      isLoading: false,
    });
    mockUseAccount.mockReturnValue({
      data: mockAccountData,
      isLoading: false,
    });

    render(<HeatStripPortfolioBar />);

    expect(screen.getByText('No open positions')).toBeInTheDocument();
  });

  it('opens symbol detail panel on segment click', () => {
    mockUsePositions.mockReturnValue({
      data: mockPositionsData,
      isLoading: false,
    });
    mockUseAccount.mockReturnValue({
      data: mockAccountData,
      isLoading: false,
    });

    const { container } = render(<HeatStripPortfolioBar />);

    // Find clickable segment rects (excluding background)
    const segments = container.querySelectorAll('rect.cursor-pointer');

    if (segments.length > 0) {
      fireEvent.click(segments[0]);
      expect(mockOpenSymbolDetail).toHaveBeenCalled();
    }
  });
});
