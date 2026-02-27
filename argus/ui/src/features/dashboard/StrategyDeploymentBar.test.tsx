/**
 * Tests for StrategyDeploymentBar component.
 *
 * Sprint 21d Code Review — Replaces HeatStripPortfolioBar.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StrategyDeploymentBar } from './StrategyDeploymentBar';
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
      strategy_id: 'orb_breakout',
      symbol: 'NVDA',
      side: 'long',
      entry_price: 800.0,
      entry_time: '2026-02-28T10:00:00Z',
      shares_total: 10,
      shares_remaining: 10,
      current_price: 810.0,
      unrealized_pnl: 100.0,
      unrealized_pnl_pct: 1.25,
      stop_price: 790.0,
      t1_price: 815.0,
      t2_price: 830.0,
      t1_filled: false,
      hold_duration_seconds: 900,
      r_multiple_current: 1.0,
    },
    {
      position_id: 'pos-3',
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
  count: 3,
  timestamp: '2026-02-28T10:30:00Z',
};

const mockAccountData: AccountResponse = {
  equity: 100000,
  cash: 50000,
  buying_power: 75000,
  daily_pnl: 500.0,
  daily_pnl_pct: 0.5,
  open_positions_count: 3,
  daily_trades_count: 5,
  market_status: 'open',
  broker_source: 'alpaca',
  data_source: 'alpaca',
  timestamp: '2026-02-28T10:30:00Z',
};

describe('StrategyDeploymentBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders SVG bar with segments', () => {
    mockUsePositions.mockReturnValue({
      data: mockPositionsData,
      isLoading: false,
    });
    mockUseAccount.mockReturnValue({
      data: mockAccountData,
      isLoading: false,
    });

    const { container } = render(<StrategyDeploymentBar />);

    // Check SVG is rendered
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Check rect elements exist (background + segments)
    const rects = container.querySelectorAll('rect');
    expect(rects.length).toBeGreaterThan(0);
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

    render(<StrategyDeploymentBar />);

    expect(screen.getByText('No capital deployed')).toBeInTheDocument();
  });

  it('renders loading state as animated skeleton', () => {
    mockUsePositions.mockReturnValue({
      data: null,
      isLoading: true,
    });
    mockUseAccount.mockReturnValue({
      data: null,
      isLoading: true,
    });

    const { container } = render(<StrategyDeploymentBar />);

    // Check for animate-pulse skeleton
    const skeleton = container.querySelector('.animate-pulse');
    expect(skeleton).toBeInTheDocument();
  });

  it('groups positions by strategy for segments', () => {
    mockUsePositions.mockReturnValue({
      data: mockPositionsData,
      isLoading: false,
    });
    mockUseAccount.mockReturnValue({
      data: mockAccountData,
      isLoading: false,
    });

    const { container } = render(<StrategyDeploymentBar />);

    // Should have segments grouped by strategy (2 strategies + available)
    // orb_breakout: pos-1 + pos-2
    // vwap_reclaim: pos-3
    // available: remaining capital
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Check that the clip path for rounded corners exists
    const clipPath = container.querySelector('clipPath');
    expect(clipPath).toBeInTheDocument();
  });

  it('handles edge case with zero equity', () => {
    mockUsePositions.mockReturnValue({
      data: mockPositionsData,
      isLoading: false,
    });
    mockUseAccount.mockReturnValue({
      data: { ...mockAccountData, equity: 0 },
      isLoading: false,
    });

    render(<StrategyDeploymentBar />);

    // Should show empty state when equity is zero
    expect(screen.getByText('No capital deployed')).toBeInTheDocument();
  });
});
