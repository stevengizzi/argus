/**
 * PerformancePage integration tests.
 *
 * Sprint 21d Session 9: Tab switching and full integration tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PerformancePage } from './PerformancePage';

// Mock the hooks
vi.mock('../hooks/usePerformance', () => ({
  usePerformance: vi.fn(),
  usePreviousPeriodPerformance: vi.fn(),
}));

// Mock LWChart to avoid Lightweight Charts initialization
vi.mock('../components/LWChart', () => ({
  LWChart: ({ height }: { height: number }) => (
    <div data-testid="lw-chart" style={{ height: `${height}px` }} />
  ),
}));

// Mock chart animation
vi.mock('../utils/chartAnimation', () => ({
  animateChartDrawIn: vi.fn(),
}));

// Mock the individual tab components to simplify testing
vi.mock('../features/performance/TradeActivityHeatmap', () => ({
  TradeActivityHeatmap: () => <div data-testid="trade-activity-heatmap">Heatmap</div>,
}));

vi.mock('../features/performance/CalendarPnlView', () => ({
  CalendarPnlView: () => <div data-testid="calendar-pnl-view">Calendar</div>,
}));

vi.mock('../features/performance/RMultipleHistogram', () => ({
  RMultipleHistogram: () => <div data-testid="r-multiple-histogram">Histogram</div>,
}));

vi.mock('../features/performance/RiskWaterfall', () => ({
  RiskWaterfall: () => <div data-testid="risk-waterfall">Waterfall</div>,
}));

vi.mock('../features/performance/PortfolioTreemap', () => ({
  PortfolioTreemap: () => <div data-testid="portfolio-treemap">Treemap</div>,
}));

vi.mock('../features/performance/CorrelationMatrix', () => ({
  CorrelationMatrix: () => <div data-testid="correlation-matrix">Matrix</div>,
}));

import { usePerformance, usePreviousPeriodPerformance } from '../hooks/usePerformance';

const mockPerformanceData = {
  period: 'month',
  date_from: '2026-02-01',
  date_to: '2026-02-28',
  metrics: {
    total_trades: 45,
    win_rate: 0.65,
    profit_factor: 2.1,
    net_pnl: 3500,
    gross_pnl: 4200,
    total_commissions: 45,
    avg_r_multiple: 0.8,
    sharpe_ratio: 2.5,
    max_drawdown_pct: 3.2,
    avg_hold_seconds: 1800,
    largest_win: 850,
    largest_loss: -320,
    consecutive_wins_max: 5,
    consecutive_losses_max: 2,
  },
  daily_pnl: [
    { date: '2026-02-01', pnl: 100, trades: 2 },
    { date: '2026-02-02', pnl: 150, trades: 3 },
    { date: '2026-02-03', pnl: -50, trades: 1 },
  ],
  by_strategy: {
    strat_orb_breakout: {
      total_trades: 25,
      win_rate: 0.68,
      net_pnl: 2000,
      profit_factor: 2.4,
    },
  },
  timestamp: '2026-02-28T12:00:00Z',
};

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('PerformancePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementation
    vi.mocked(usePerformance).mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof usePerformance>);

    vi.mocked(usePreviousPeriodPerformance).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof usePreviousPeriodPerformance>);
  });

  it('renders the performance page with title and tabs', () => {
    renderWithProviders(<PerformancePage />);

    // Should show the title
    expect(screen.getByText('Performance')).toBeInTheDocument();

    // Should show all tabs
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Heatmaps' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Distribution' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Portfolio' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Replay' })).toBeInTheDocument();
  });

  it('shows Overview tab content by default', () => {
    renderWithProviders(<PerformancePage />);

    // Overview tab should be active and show MetricsGrid (Trades appears in both MetricsGrid and StrategyBreakdown)
    const tradesElements = screen.getAllByText('Trades');
    expect(tradesElements.length).toBeGreaterThan(0);
    expect(screen.getByText('45')).toBeInTheDocument();

    // Should show EquityCurve
    expect(screen.getByText('Equity Curve')).toBeInTheDocument();

    // Should show StrategyBreakdown (label is "By Strategy")
    expect(screen.getByText('By Strategy')).toBeInTheDocument();
  });

  it('switches to Heatmaps tab on click', async () => {
    renderWithProviders(<PerformancePage />);

    // Click Heatmaps tab
    const heatmapsTab = screen.getByRole('tab', { name: 'Heatmaps' });
    fireEvent.click(heatmapsTab);

    // Should show heatmaps content
    await waitFor(() => {
      expect(screen.getByTestId('trade-activity-heatmap')).toBeInTheDocument();
      expect(screen.getByTestId('calendar-pnl-view')).toBeInTheDocument();
    });

    // Overview content should not be visible
    expect(screen.queryByText('Trades')).not.toBeInTheDocument();
  });

  it('switches to Distribution tab on click', async () => {
    renderWithProviders(<PerformancePage />);

    // Click Distribution tab
    const distributionTab = screen.getByRole('tab', { name: 'Distribution' });
    fireEvent.click(distributionTab);

    // Should show distribution content
    await waitFor(() => {
      expect(screen.getByTestId('r-multiple-histogram')).toBeInTheDocument();
      expect(screen.getByTestId('risk-waterfall')).toBeInTheDocument();
    });
  });

  it('switches to Portfolio tab on click', async () => {
    renderWithProviders(<PerformancePage />);

    // Click Portfolio tab
    const portfolioTab = screen.getByRole('tab', { name: 'Portfolio' });
    fireEvent.click(portfolioTab);

    // Should show portfolio content
    await waitFor(() => {
      expect(screen.getByTestId('portfolio-treemap')).toBeInTheDocument();
      expect(screen.getByTestId('correlation-matrix')).toBeInTheDocument();
    });
  });

  it('shows Replay placeholder on Replay tab', async () => {
    renderWithProviders(<PerformancePage />);

    // Click Replay tab
    const replayTab = screen.getByRole('tab', { name: 'Replay' });
    fireEvent.click(replayTab);

    // Should show placeholder
    await waitFor(() => {
      expect(screen.getByText('Trade Replay loading in next session')).toBeInTheDocument();
    });
  });

  it('shows loading skeleton when data is loading', () => {
    vi.mocked(usePerformance).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isFetching: true,
    } as ReturnType<typeof usePerformance>);

    renderWithProviders(<PerformancePage />);

    // Should show skeleton (which uses skeleton-shimmer class)
    const skeletonElements = document.querySelectorAll('.skeleton-shimmer');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it('shows error state when fetch fails', () => {
    vi.mocked(usePerformance).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
      isFetching: false,
    } as ReturnType<typeof usePerformance>);

    renderWithProviders(<PerformancePage />);

    expect(screen.getByText('Failed to load performance data')).toBeInTheDocument();
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('shows empty state when no trades', () => {
    vi.mocked(usePerformance).mockReturnValue({
      data: {
        ...mockPerformanceData,
        metrics: { ...mockPerformanceData.metrics, total_trades: 0 },
      },
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof usePerformance>);

    renderWithProviders(<PerformancePage />);

    expect(screen.getByText('No trades for this period')).toBeInTheDocument();
  });

  it('maintains tab state when period changes', async () => {
    renderWithProviders(<PerformancePage />);

    // Switch to Distribution tab
    const distributionTab = screen.getByRole('tab', { name: 'Distribution' });
    fireEvent.click(distributionTab);

    await waitFor(() => {
      expect(screen.getByTestId('r-multiple-histogram')).toBeInTheDocument();
    });

    // Change period (via period selector button)
    const weekButton = screen.getByRole('button', { name: 'Week' });
    fireEvent.click(weekButton);

    // Tab should still be Distribution
    await waitFor(() => {
      expect(screen.getByTestId('r-multiple-histogram')).toBeInTheDocument();
    });
  });
});
