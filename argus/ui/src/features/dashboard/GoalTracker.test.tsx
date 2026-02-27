/**
 * Tests for GoalTracker component.
 *
 * Sprint 21d Session 5.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GoalTracker } from './GoalTracker';
import type { GoalsConfig, PerformanceResponse } from '../../api/types';

// Mock useGoals hook
const mockUseGoals = vi.fn();
vi.mock('../../hooks/useGoals', () => ({
  useGoals: () => mockUseGoals(),
}));

// Mock usePerformance hook
const mockUsePerformance = vi.fn();
vi.mock('../../hooks/usePerformance', () => ({
  usePerformance: () => mockUsePerformance(),
}));

const mockGoalsData: GoalsConfig = {
  monthly_target_usd: 5000,
  timestamp: '2026-02-28T10:00:00Z',
};

const createMockPerformanceData = (netPnl: number): PerformanceResponse => ({
  period: 'month',
  date_from: '2026-02-01',
  date_to: '2026-02-28',
  metrics: {
    total_trades: 50,
    win_rate: 0.6,
    profit_factor: 1.8,
    net_pnl: netPnl,
    gross_pnl: netPnl + 500,
    total_commissions: 100,
    avg_r_multiple: 0.5,
    sharpe_ratio: 1.5,
    max_drawdown_pct: 3.5,
    avg_hold_seconds: 1200,
    largest_win: 800,
    largest_loss: -400,
    consecutive_wins_max: 5,
    consecutive_losses_max: 2,
  },
  daily_pnl: [],
  by_strategy: {},
  timestamp: '2026-02-28T10:00:00Z',
});

describe('GoalTracker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders on pace state with green progress bar', () => {
    // On pace: current P&L exceeds expected progress
    mockUseGoals.mockReturnValue({
      data: mockGoalsData,
      isLoading: false,
    });
    mockUsePerformance.mockReturnValue({
      data: createMockPerformanceData(4000), // 80% of target, likely on pace mid-month
      isLoading: false,
    });

    render(<GoalTracker />);

    // Check target is displayed (formatCurrency adds decimals: $5,000.00)
    expect(screen.getByText(/Target:/)).toBeInTheDocument();
    expect(screen.getByText(/\$5,000/)).toBeInTheDocument();

    // Check current P&L is displayed (formatCurrency adds decimals: $4,000.00)
    expect(screen.getByText(/\$4,000/)).toBeInTheDocument();

    // Check progress percentage
    expect(screen.getByText(/80%/)).toBeInTheDocument();
  });

  it('renders behind pace state with amber/red progress bar', () => {
    // Behind pace: low P&L relative to target
    mockUseGoals.mockReturnValue({
      data: mockGoalsData,
      isLoading: false,
    });
    mockUsePerformance.mockReturnValue({
      data: createMockPerformanceData(500), // Only 10% of target
      isLoading: false,
    });

    render(<GoalTracker />);

    // Check current P&L (formatCurrency adds decimals: $500.00)
    expect(screen.getByText(/\$500/)).toBeInTheDocument();

    // Should show behind pace
    expect(screen.getByText(/Behind pace/)).toBeInTheDocument();
  });

  it('renders with correct percentage calculation', () => {
    mockUseGoals.mockReturnValue({
      data: mockGoalsData,
      isLoading: false,
    });
    mockUsePerformance.mockReturnValue({
      data: createMockPerformanceData(2500), // 50% of target
      isLoading: false,
    });

    render(<GoalTracker />);

    // Check percentage is calculated correctly
    expect(screen.getByText(/\$2,500/)).toBeInTheDocument();
    expect(screen.getByText(/50%/)).toBeInTheDocument();
  });
});
