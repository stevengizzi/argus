/**
 * Tests for PreMarketLayout component.
 *
 * Sprint 21d Session 5.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PreMarketLayout } from './PreMarketLayout';

// Mock useGoals hook
vi.mock('../../hooks/useGoals', () => ({
  useGoals: () => ({
    data: { monthly_target_usd: 5000, timestamp: '2026-02-28T10:00:00Z' },
    isLoading: false,
  }),
}));

// Mock usePerformance hook
vi.mock('../../hooks/usePerformance', () => ({
  usePerformance: () => ({
    data: {
      period: 'month',
      date_from: '2026-02-01',
      date_to: '2026-02-28',
      metrics: {
        total_trades: 50,
        win_rate: 0.6,
        profit_factor: 1.8,
        net_pnl: 3000,
        gross_pnl: 3500,
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
    },
    isLoading: false,
  }),
}));

// Mock useSessionSummary hook
vi.mock('../../hooks/useSessionSummary', () => ({
  useSessionSummary: () => ({
    data: null,
    isLoading: false,
  }),
}));

// Mock useIsMultiColumn hook
const mockUseIsMultiColumn = vi.fn();
vi.mock('../../hooks/useMediaQuery', () => ({
  useIsMultiColumn: () => mockUseIsMultiColumn(),
}));

describe('PreMarketLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseIsMultiColumn.mockReturnValue(true); // Default: desktop/tablet
  });

  it('renders countdown and placeholder cards', () => {
    render(<PreMarketLayout />);

    // Check countdown section exists (shows either "Market Opens In" or "Market Open")
    const hasCountdown =
      screen.queryByText(/Market Opens In/i) !== null ||
      screen.queryByText(/Market Open/i) !== null;
    expect(hasCountdown).toBe(true);

    // Check placeholder cards exist
    expect(screen.getByText('Ranked Watchlist')).toBeInTheDocument();
    expect(screen.getByText('Regime Forecast')).toBeInTheDocument();
    expect(screen.getByText('Catalyst Summary')).toBeInTheDocument();

    // Check sprint activation notes
    expect(screen.getByText(/Pre-Market Intelligence activating Sprint 23/)).toBeInTheDocument();
    expect(screen.getByText(/AI-powered regime forecast available Sprint 22/)).toBeInTheDocument();
    expect(screen.getByText(/NLP Catalyst Pipeline activating Sprint 23/)).toBeInTheDocument();
  });

  it('renders mobile layout in single column', () => {
    mockUseIsMultiColumn.mockReturnValue(false);

    render(<PreMarketLayout />);

    // Should still render the main elements
    expect(screen.getByText('Ranked Watchlist')).toBeInTheDocument();
    expect(screen.getByText('Regime Forecast')).toBeInTheDocument();
    expect(screen.getByText('Catalyst Summary')).toBeInTheDocument();
  });
});
