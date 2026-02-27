/**
 * Tests for GoalTracker component.
 *
 * Sprint 21d Code Review — Enhanced GoalTracker with 2-column layout.
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

  it('renders Monthly Goal header', () => {
    mockUseGoals.mockReturnValue({
      data: mockGoalsData,
      isLoading: false,
    });
    mockUsePerformance.mockReturnValue({
      data: createMockPerformanceData(4000),
      isLoading: false,
    });

    render(<GoalTracker />);

    expect(screen.getByText('Monthly Goal')).toBeInTheDocument();
  });

  it('renders target amount and current P&L', () => {
    mockUseGoals.mockReturnValue({
      data: mockGoalsData,
      isLoading: false,
    });
    mockUsePerformance.mockReturnValue({
      data: createMockPerformanceData(4000),
      isLoading: false,
    });

    render(<GoalTracker />);

    // Check target is displayed
    expect(screen.getByText(/Target:/)).toBeInTheDocument();
    expect(screen.getByText(/\$5,000/)).toBeInTheDocument();

    // Check current P&L is displayed
    expect(screen.getByText(/\$4,000/)).toBeInTheDocument();

    // Check progress percentage
    expect(screen.getByText(/80%/)).toBeInTheDocument();
  });

  it('renders progress percentage at 50%', () => {
    mockUseGoals.mockReturnValue({
      data: mockGoalsData,
      isLoading: false,
    });
    mockUsePerformance.mockReturnValue({
      data: createMockPerformanceData(2500),
      isLoading: false,
    });

    render(<GoalTracker />);

    // 50% progress
    expect(screen.getByText(/\$2,500/)).toBeInTheDocument();
    expect(screen.getByText(/50%/)).toBeInTheDocument();
  });

  it('renders behind pace state with Behind pace label', () => {
    mockUseGoals.mockReturnValue({
      data: mockGoalsData,
      isLoading: false,
    });
    mockUsePerformance.mockReturnValue({
      data: createMockPerformanceData(500), // Only 10% of target
      isLoading: false,
    });

    render(<GoalTracker />);

    // Should show behind pace (low P&L relative to expected progress)
    expect(screen.getByText(/Behind pace/)).toBeInTheDocument();
  });

  it('renders Avg daily and Need/day stats', () => {
    mockUseGoals.mockReturnValue({
      data: mockGoalsData,
      isLoading: false,
    });
    mockUsePerformance.mockReturnValue({
      data: createMockPerformanceData(2000),
      isLoading: false,
    });

    render(<GoalTracker />);

    // Check stats labels are present
    expect(screen.getByText('Avg daily:')).toBeInTheDocument();
    expect(screen.getByText('Need/day:')).toBeInTheDocument();
  });

  it('renders days left in month', () => {
    mockUseGoals.mockReturnValue({
      data: mockGoalsData,
      isLoading: false,
    });
    mockUsePerformance.mockReturnValue({
      data: createMockPerformanceData(3000),
      isLoading: false,
    });

    render(<GoalTracker />);

    // Should show days remaining (variable based on current date)
    expect(screen.getByText(/day.*left/i)).toBeInTheDocument();
  });

  it('renders loading skeleton when data is loading', () => {
    mockUseGoals.mockReturnValue({
      data: null,
      isLoading: true,
    });
    mockUsePerformance.mockReturnValue({
      data: null,
      isLoading: true,
    });

    const { container } = render(<GoalTracker />);

    // Check for skeleton animation
    const pulsingElements = container.querySelectorAll('.animate-pulse');
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  // Sprint 21d: Props-based rendering tests (dashboard summary mode)
  describe('with props (dashboard summary mode)', () => {
    it('renders data from props without loading state', () => {
      // Hooks return loading state but should be ignored when props provided
      mockUseGoals.mockReturnValue({ data: null, isLoading: true });
      mockUsePerformance.mockReturnValue({ data: null, isLoading: true });

      const { container } = render(
        <GoalTracker
          data={{
            monthly_target_usd: 6000,
            current_month_pnl: 4500,
            trading_days_elapsed: 15,
            trading_days_remaining: 5,
            avg_daily_pnl: 300,
            needed_daily_pnl: 300,
            pace_status: 'ahead',
          }}
        />
      );

      // Should NOT show loading state
      const pulsingElements = container.querySelectorAll('.animate-pulse');
      expect(pulsingElements.length).toBe(0);

      // Should show values from props
      expect(screen.getByText(/\$6,000/)).toBeInTheDocument();
      expect(screen.getByText(/\$4,500/)).toBeInTheDocument();
      expect(screen.getByText(/5 day.*left/i)).toBeInTheDocument();
      expect(screen.getByText('Ahead of pace')).toBeInTheDocument();
    });

    it('renders correct pace status from props', () => {
      mockUseGoals.mockReturnValue({ data: null, isLoading: false });
      mockUsePerformance.mockReturnValue({ data: null, isLoading: false });

      // Test "behind" pace status
      render(
        <GoalTracker
          data={{
            monthly_target_usd: 5000,
            current_month_pnl: 1000,
            trading_days_elapsed: 18,
            trading_days_remaining: 2,
            avg_daily_pnl: 55.56,
            needed_daily_pnl: 2000,
            pace_status: 'behind',
          }}
        />
      );

      expect(screen.getByText('Behind pace')).toBeInTheDocument();
    });
  });
});
