/**
 * Tests for PatternLibraryPage query param handling.
 *
 * Sprint 21d: Tests for auto-selecting strategy from URL query param.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PatternLibraryPage } from './PatternLibraryPage';
import { usePatternLibraryUI } from '../stores/patternLibraryUI';
import type { StrategyInfo } from '../api/types';

// Mock strategies data
const mockStrategies: StrategyInfo[] = [
  {
    strategy_id: 'strat_orb_breakout',
    name: 'ORB Breakout',
    version: '1.0.0',
    is_active: true,
    pipeline_stage: 'paper_trading',
    allocated_capital: 10000,
    daily_pnl: 150,
    trade_count_today: 3,
    open_positions: 1,
    config_summary: {},
    time_window: '9:30 AM – 10:00 AM',
    family: 'orb_family',
    description_short: 'Opening range breakout strategy',
    performance_summary: null,
    backtest_summary: null,
  },
  {
    strategy_id: 'strat_vwap_reclaim',
    name: 'VWAP Reclaim',
    version: '1.0.0',
    is_active: true,
    pipeline_stage: 'live_full',
    allocated_capital: 15000,
    daily_pnl: 200,
    trade_count_today: 2,
    open_positions: 0,
    config_summary: {},
    time_window: '10:00 AM – 2:00 PM',
    family: 'momentum',
    description_short: 'VWAP reclaim strategy',
    performance_summary: null,
    backtest_summary: null,
  },
];

// Mock the useStrategies hook
vi.mock('../hooks/useStrategies', () => ({
  useStrategies: () => ({
    data: { strategies: mockStrategies },
    isLoading: false,
  }),
}));

// Mock the useSortedStrategies hook
vi.mock('../hooks/useSortedStrategies', () => ({
  useSortedStrategies: (strategies: StrategyInfo[]) => strategies,
}));

// Mock PatternCardGrid to avoid complex rendering
vi.mock('../features/patterns/PatternCardGrid', () => ({
  PatternCardGrid: ({ selectedId }: { selectedId: string | null }) => (
    <div data-testid="pattern-card-grid" data-selected-id={selectedId}>
      Pattern Card Grid
    </div>
  ),
}));

// Mock PatternDetail
vi.mock('../features/patterns/PatternDetail', () => ({
  PatternDetail: ({ strategyId }: { strategyId: string }) => (
    <div data-testid="pattern-detail" data-strategy-id={strategyId}>
      Pattern Detail
    </div>
  ),
}));

// Mock IncubatorPipeline
vi.mock('../features/patterns/IncubatorPipeline', () => ({
  IncubatorPipeline: () => <div data-testid="incubator-pipeline">Pipeline</div>,
}));

// Mock AnimatedPage
vi.mock('../components/AnimatedPage', () => ({
  AnimatedPage: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe('PatternLibraryPage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    // Reset Zustand store
    usePatternLibraryUI.setState({
      selectedStrategyId: null,
      activeTab: 'overview',
      filters: { stage: null, family: null, timeWindow: null },
      sortBy: 'name',
    });
  });

  it('auto-selects strategy from query param on mount', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/patterns?strategy=strat_orb_breakout']}>
          <PatternLibraryPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Wait for the strategy to be selected
    await waitFor(() => {
      const state = usePatternLibraryUI.getState();
      expect(state.selectedStrategyId).toBe('strat_orb_breakout');
    });
  });

  it('does not select strategy if query param is invalid', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/patterns?strategy=invalid_strategy']}>
          <PatternLibraryPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Wait for render to complete
    await waitFor(() => {
      const state = usePatternLibraryUI.getState();
      // Should remain null since 'invalid_strategy' is not in the list
      expect(state.selectedStrategyId).toBeNull();
    });
  });

  it('does not change selection if no query param present', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/patterns']}>
          <PatternLibraryPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Wait for render to complete
    await waitFor(() => {
      const state = usePatternLibraryUI.getState();
      expect(state.selectedStrategyId).toBeNull();
    });
  });

  it('shows detail panel when strategy is selected', async () => {
    // Pre-set a selected strategy
    usePatternLibraryUI.setState({ selectedStrategyId: 'strat_vwap_reclaim' });

    const { getByTestId } = render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/patterns']}>
          <PatternLibraryPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      const detailPanel = getByTestId('pattern-detail');
      expect(detailPanel).toBeInTheDocument();
      expect(detailPanel.getAttribute('data-strategy-id')).toBe('strat_vwap_reclaim');
    });
  });
});
