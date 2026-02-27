/**
 * Tests for TodayStats component.
 *
 * Sprint 21d Code Review — New component for dashboard 3-card row.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TodayStats } from './TodayStats';
import type { PerformanceResponse, TradesResponse } from '../../api/types';

// Mock hooks
const mockUsePerformance = vi.fn();
vi.mock('../../hooks/usePerformance', () => ({
  usePerformance: () => mockUsePerformance(),
}));

const mockUseTrades = vi.fn();
vi.mock('../../hooks/useTrades', () => ({
  useTrades: () => mockUseTrades(),
}));

const today = new Date().toISOString().split('T')[0];

const mockPerformanceData: PerformanceResponse = {
  period: 'day',
  date_from: today,
  date_to: today,
  metrics: {
    total_trades: 12,
    win_rate: 58,
    profit_factor: 1.8,
    net_pnl: 850,
    gross_pnl: 950,
    total_commissions: 100,
    avg_r_multiple: 0.7,
    sharpe_ratio: 1.5,
    max_drawdown_pct: 2.5,
    avg_hold_seconds: 1200,
    largest_win: 350,
    largest_loss: -200,
    consecutive_wins_max: 4,
    consecutive_losses_max: 2,
  },
  daily_pnl: [],
  by_strategy: {},
  timestamp: `${today}T10:30:00Z`,
};

const mockTradesData: TradesResponse = {
  trades: [
    {
      id: 'trade-1',
      strategy_id: 'orb_breakout',
      symbol: 'NVDA',
      asset_class: 'us_stocks',
      side: 'buy',
      entry_price: 850,
      entry_time: `${today}T09:45:00Z`,
      exit_price: 865,
      exit_time: `${today}T10:30:00Z`,
      shares: 20,
      stop_price: 840,
      target_prices: [860, 870],
      exit_reason: 'target_1',
      gross_pnl: 300,
      commission: 2,
      r_multiple: 1.5,
      realized_pnl: 298,
    },
    {
      id: 'trade-2',
      strategy_id: 'vwap_reclaim',
      symbol: 'AAPL',
      asset_class: 'us_stocks',
      side: 'buy',
      entry_price: 180,
      entry_time: `${today}T10:00:00Z`,
      exit_price: 178,
      exit_time: `${today}T10:20:00Z`,
      shares: 50,
      stop_price: 177,
      target_prices: [183, 185],
      exit_reason: 'stop_loss',
      gross_pnl: -100,
      commission: 1,
      r_multiple: -1.0,
      realized_pnl: -101,
    },
  ],
  count: 2,
  total_count: 2,
  limit: 100,
  offset: 0,
  timestamp: `${today}T10:30:00Z`,
};

describe('TodayStats', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Today\'s Stats header', () => {
    mockUsePerformance.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
    });
    mockUseTrades.mockReturnValue({
      data: mockTradesData,
      isLoading: false,
    });

    render(<TodayStats />);

    expect(screen.getByText("Today's Stats")).toBeInTheDocument();
  });

  it('renders trades count', () => {
    mockUsePerformance.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
    });
    mockUseTrades.mockReturnValue({
      data: mockTradesData,
      isLoading: false,
    });

    render(<TodayStats />);

    expect(screen.getByText('Trades')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('renders win rate with percentage', () => {
    mockUsePerformance.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
    });
    mockUseTrades.mockReturnValue({
      data: mockTradesData,
      isLoading: false,
    });

    render(<TodayStats />);

    expect(screen.getByText('Win Rate')).toBeInTheDocument();
    expect(screen.getByText('58%')).toBeInTheDocument();
  });

  it('renders avg R-multiple', () => {
    mockUsePerformance.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
    });
    mockUseTrades.mockReturnValue({
      data: mockTradesData,
      isLoading: false,
    });

    render(<TodayStats />);

    expect(screen.getByText('Avg R')).toBeInTheDocument();
    expect(screen.getByText('+0.7R')).toBeInTheDocument();
  });

  it('renders best trade with symbol and P&L', () => {
    mockUsePerformance.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
    });
    mockUseTrades.mockReturnValue({
      data: mockTradesData,
      isLoading: false,
    });

    render(<TodayStats />);

    expect(screen.getByText('Best Trade')).toBeInTheDocument();
    expect(screen.getByText('NVDA')).toBeInTheDocument();
    // Check for the P&L value (formatted as currency)
    expect(screen.getByText(/\+\$298/)).toBeInTheDocument();
  });

  it('renders loading skeleton when data is loading', () => {
    mockUsePerformance.mockReturnValue({
      data: null,
      isLoading: true,
    });
    mockUseTrades.mockReturnValue({
      data: null,
      isLoading: true,
    });

    const { container } = render(<TodayStats />);

    // Check for skeleton animation
    const pulsingElements = container.querySelectorAll('.animate-pulse');
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  it('renders placeholder when no trades today', () => {
    mockUsePerformance.mockReturnValue({
      data: {
        ...mockPerformanceData,
        metrics: {
          ...mockPerformanceData.metrics,
          total_trades: 0,
          win_rate: 0,
          avg_r_multiple: 0,
        },
      },
      isLoading: false,
    });
    mockUseTrades.mockReturnValue({
      data: { trades: [], count: 0, total_count: 0, limit: 100, offset: 0, timestamp: '' },
      isLoading: false,
    });

    render(<TodayStats />);

    // Should show 0 trades
    expect(screen.getByText('0')).toBeInTheDocument();
    // Should show placeholder dashes for missing data
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThan(0);
  });
});
