/**
 * StrategyCards component tests.
 *
 * Sprint 20: Verify Afternoon Momentum appears in strategy list.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrategyCards } from './StrategyCards';
import type { StrategiesResponse } from '../../api/types';

// Mock useStrategies hook
const mockStrategiesData: StrategiesResponse = {
  strategies: [
    {
      strategy_id: 'orb_breakout',
      name: 'ORB Breakout',
      version: '1.0.0',
      is_active: true,
      pipeline_stage: 'paper',
      allocated_capital: 20000,
      daily_pnl: 150.50,
      trade_count_today: 3,
      open_positions: 1,
      config_summary: { or: 5, hold: 120 },
    },
    {
      strategy_id: 'orb_scalp',
      name: 'ORB Scalp',
      version: '1.0.0',
      is_active: true,
      pipeline_stage: 'paper',
      allocated_capital: 20000,
      daily_pnl: -45.25,
      trade_count_today: 5,
      open_positions: 2,
      config_summary: { target_r: 0.3, hold: 2 },
    },
    {
      strategy_id: 'vwap_reclaim',
      name: 'VWAP Reclaim',
      version: '1.0.0',
      is_active: true,
      pipeline_stage: 'paper',
      allocated_capital: 20000,
      daily_pnl: 85.00,
      trade_count_today: 2,
      open_positions: 1,
      config_summary: { pullback_depth: 0.5, bars: 15 },
    },
    {
      strategy_id: 'afternoon_momentum',
      name: 'Afternoon Momentum',
      version: '1.0.0',
      is_active: true,
      pipeline_stage: 'paper',
      allocated_capital: 20000,
      daily_pnl: 120.75,
      trade_count_today: 2,
      open_positions: 1,
      config_summary: { consolidation_atr_ratio: 0.75, min_bars: 30 },
    },
  ],
  timestamp: new Date().toISOString(),
};

vi.mock('../../hooks/useStrategies', () => ({
  useStrategies: vi.fn(() => ({
    data: mockStrategiesData,
    isLoading: false,
    error: null,
  })),
}));

vi.mock('../../hooks/useControls', () => ({
  usePauseStrategy: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
    reset: vi.fn(),
  })),
  useResumeStrategy: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
    reset: vi.fn(),
  })),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('StrategyCards', () => {
  it('renders all four strategies', () => {
    render(<StrategyCards />, { wrapper: createWrapper() });

    // All four strategies should be visible
    expect(screen.getByText('ORB Breakout')).toBeInTheDocument();
    expect(screen.getByText('ORB Scalp')).toBeInTheDocument();
    expect(screen.getByText('VWAP Reclaim')).toBeInTheDocument();
    expect(screen.getByText('Afternoon Momentum')).toBeInTheDocument();
  });

  it('shows correct count subtitle for four strategies', () => {
    render(<StrategyCards />, { wrapper: createWrapper() });

    expect(screen.getByText('4 configured')).toBeInTheDocument();
  });

  it('shows Afternoon Momentum allocation amount', () => {
    render(<StrategyCards />, { wrapper: createWrapper() });

    // Should show $20,000 for each strategy (formatCurrencyCompact)
    // Multiple strategies show this, so getAllByText
    const allocations = screen.getAllByText('$20,000');
    expect(allocations.length).toBe(4);
  });

  it('shows Afternoon Momentum daily P&L', () => {
    render(<StrategyCards />, { wrapper: createWrapper() });

    // Afternoon Momentum has $120.75 P&L
    expect(screen.getByText('+$120.75')).toBeInTheDocument();
  });

  it('shows Afternoon Momentum open positions', () => {
    render(<StrategyCards />, { wrapper: createWrapper() });

    // All four strategies have open positions (1, 2, 1, 1)
    // The Open label appears for each
    const openLabels = screen.getAllByText('Open');
    expect(openLabels.length).toBe(4);
  });
});

describe('StrategyCards - Empty state', () => {
  it('shows empty state when no strategies', async () => {
    const { useStrategies } = await import('../../hooks/useStrategies');
    vi.mocked(useStrategies).mockReturnValue({
      data: { strategies: [], timestamp: new Date().toISOString() },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useStrategies>);

    render(<StrategyCards />, { wrapper: createWrapper() });

    expect(screen.getByText('No strategies are currently configured.')).toBeInTheDocument();
  });
});
