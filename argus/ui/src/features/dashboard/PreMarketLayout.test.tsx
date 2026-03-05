/**
 * Tests for PreMarketLayout component.
 *
 * Sprint 21d Session 5 + Sprint 21.7 Session 3 (PreMarketWatchlistPanel).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PreMarketLayout } from './PreMarketLayout';
import type { WatchlistResponse } from '../../api/types';

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

// Mock useWatchlist hook
const mockUseWatchlist = vi.fn();
vi.mock('../../hooks/useWatchlist', () => ({
  useWatchlist: () => mockUseWatchlist(),
}));

// Factory for mock watchlist data
function createMockWatchlistData(overrides: Partial<WatchlistResponse> = {}): WatchlistResponse {
  return {
    symbols: [
      {
        symbol: 'TSLA',
        current_price: 250.50,
        gap_pct: 3.2,
        strategies: ['orb'],
        vwap_state: 'watching',
        sparkline: [],
        vwap_distance_pct: null,
        scan_source: 'fmp',
        selection_reason: 'gap_up_3.2%',
      },
      {
        symbol: 'NVDA',
        current_price: 875.00,
        gap_pct: -1.8,
        strategies: ['vwap_reclaim'],
        vwap_state: 'watching',
        sparkline: [],
        vwap_distance_pct: null,
        scan_source: 'fmp',
        selection_reason: 'gap_down_1.8%',
      },
    ],
    count: 2,
    timestamp: '2026-03-05T08:00:00Z',
    ...overrides,
  };
}

describe('PreMarketLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseIsMultiColumn.mockReturnValue(true); // Default: desktop/tablet
    // Default watchlist mock with FMP data
    mockUseWatchlist.mockReturnValue({
      data: createMockWatchlistData(),
      isLoading: false,
      isError: false,
    });
  });

  it('renders countdown and placeholder cards', () => {
    render(<PreMarketLayout />);

    // Check countdown section exists (shows either "Market Opens In" or "Market Open")
    const hasCountdown =
      screen.queryByText(/Market Opens In/i) !== null ||
      screen.queryByText(/Market Open/i) !== null;
    expect(hasCountdown).toBe(true);

    // Check cards exist (Pre-Market Watchlist is now live, others are placeholders)
    expect(screen.getByText('Pre-Market Watchlist')).toBeInTheDocument();
    expect(screen.getByText('Regime Forecast')).toBeInTheDocument();
    expect(screen.getByText('Catalyst Summary')).toBeInTheDocument();

    // Check sprint activation notes for remaining placeholders
    expect(screen.getByText(/AI-powered regime forecast available Sprint 22/)).toBeInTheDocument();
    expect(screen.getByText(/NLP Catalyst Pipeline activating Sprint 23/)).toBeInTheDocument();
  });

  it('renders mobile layout in single column', () => {
    mockUseIsMultiColumn.mockReturnValue(false);

    render(<PreMarketLayout />);

    // Should still render the main elements
    expect(screen.getByText('Pre-Market Watchlist')).toBeInTheDocument();
    expect(screen.getByText('Regime Forecast')).toBeInTheDocument();
    expect(screen.getByText('Catalyst Summary')).toBeInTheDocument();
  });
});

describe('PreMarketWatchlistPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseIsMultiColumn.mockReturnValue(true);
  });

  it('renders with mock watchlist data showing symbols', () => {
    mockUseWatchlist.mockReturnValue({
      data: createMockWatchlistData(),
      isLoading: false,
      isError: false,
    });

    render(<PreMarketLayout />);

    // Check panel title
    expect(screen.getByText('Pre-Market Watchlist')).toBeInTheDocument();

    // Check symbols are rendered
    expect(screen.getByText('TSLA')).toBeInTheDocument();
    expect(screen.getByText('NVDA')).toBeInTheDocument();

    // Check gap percentages (formatted)
    expect(screen.getByText('+3.2%')).toBeInTheDocument();
    expect(screen.getByText('-1.8%')).toBeInTheDocument();
  });

  it('shows FMP badge when scan_source is fmp', () => {
    mockUseWatchlist.mockReturnValue({
      data: createMockWatchlistData({
        symbols: [
          {
            symbol: 'AAPL',
            current_price: 180.00,
            gap_pct: 2.5,
            strategies: ['orb'],
            vwap_state: 'watching',
            sparkline: [],
            vwap_distance_pct: null,
            scan_source: 'fmp',
            selection_reason: 'gap_up_2.5%',
          },
        ],
      }),
      isLoading: false,
      isError: false,
    });

    render(<PreMarketLayout />);

    // FMP badge should be shown (success variant shows green)
    expect(screen.getByText('FMP')).toBeInTheDocument();
  });

  it('shows Static badge when scan_source is static', () => {
    mockUseWatchlist.mockReturnValue({
      data: createMockWatchlistData({
        symbols: [
          {
            symbol: 'AAPL',
            current_price: 180.00,
            gap_pct: 2.5,
            strategies: ['orb'],
            vwap_state: 'watching',
            sparkline: [],
            vwap_distance_pct: null,
            scan_source: 'static',
            selection_reason: 'gap_up_2.5%',
          },
        ],
      }),
      isLoading: false,
      isError: false,
    });

    render(<PreMarketLayout />);

    // Static badge should be shown (neutral variant)
    expect(screen.getByText('Static')).toBeInTheDocument();
  });

  it('renders loading skeleton when isLoading is true', () => {
    mockUseWatchlist.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });

    render(<PreMarketLayout />);

    // Panel title should still be visible
    expect(screen.getByText('Pre-Market Watchlist')).toBeInTheDocument();

    // Table headers should be present
    expect(screen.getByText('#')).toBeInTheDocument();
    expect(screen.getByText('Symbol')).toBeInTheDocument();
    expect(screen.getByText('Gap%')).toBeInTheDocument();
    expect(screen.getByText('Reason')).toBeInTheDocument();

    // Skeleton elements should be present (5 rows × 4 columns = 20 skeleton elements)
    const skeletons = document.querySelectorAll('.skeleton-shimmer');
    expect(skeletons.length).toBeGreaterThanOrEqual(5);
  });

  it('renders empty state when watchlist has 0 symbols', () => {
    mockUseWatchlist.mockReturnValue({
      data: createMockWatchlistData({ symbols: [], count: 0 }),
      isLoading: false,
      isError: false,
    });

    render(<PreMarketLayout />);

    // Panel title should still be visible
    expect(screen.getByText('Pre-Market Watchlist')).toBeInTheDocument();

    // Empty state message should be shown
    expect(screen.getByText(/No symbols selected yet/)).toBeInTheDocument();
  });
});
