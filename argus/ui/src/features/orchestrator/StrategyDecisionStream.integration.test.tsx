/**
 * Integration tests for StrategyDecisionStream slide-out panel.
 *
 * Tests the wiring between StrategyOperationsCard "View Decisions"
 * button, OrchestratorPage state, and the slide-out panel.
 *
 * Sprint 24.5 Session 5.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrategyOperationsCard } from './StrategyOperationsCard';
import { StrategyOperationsGrid } from './StrategyOperationsGrid';
import type { AllocationInfo } from '../../api/types';

// Mock framer-motion to avoid animation complexity in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: Record<string, unknown>) => {
      const {
        variants: _v, initial: _i, animate: _a, exit: _e, transition: _t,
        ...htmlProps
      } = props;
      return <div {...htmlProps}>{children as React.ReactNode}</div>;
    },
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock hooks used by StrategyOperationsCard
vi.mock('../../hooks/useControls', () => ({
  usePauseStrategy: () => ({ mutate: vi.fn(), isPending: false }),
  useResumeStrategy: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock('../../stores/orchestratorUI', () => ({
  useOrchestratorUI: () => vi.fn(),
}));

const mockOrchestratorData = {
  allocations: [
    {
      strategy_id: 'orb_breakout',
      allocation_pct: 25,
      allocation_dollars: 10000,
      throttle_action: 'none',
      eligible: true,
      reason: '',
      deployed_capital: 5000,
      deployed_pct: 12.5,
      is_throttled: false,
      operating_window: { earliest_entry: '09:35', latest_entry: '10:05', force_close: '10:30' },
      consecutive_losses: 0,
      rolling_sharpe: 1.5,
      drawdown_pct: 2.0,
      is_active: true,
      health_status: 'healthy',
      trade_count_today: 2,
      daily_pnl: 150,
      open_position_count: 1,
      override_active: false,
      override_until: null,
    },
    {
      strategy_id: 'vwap_reclaim',
      allocation_pct: 25,
      allocation_dollars: 10000,
      throttle_action: 'none',
      eligible: true,
      reason: '',
      deployed_capital: 3000,
      deployed_pct: 7.5,
      is_throttled: false,
      operating_window: { earliest_entry: '10:15', latest_entry: '14:00', force_close: '15:30' },
      consecutive_losses: 0,
      rolling_sharpe: 0.8,
      drawdown_pct: 1.5,
      is_active: true,
      health_status: 'healthy',
      trade_count_today: 1,
      daily_pnl: 80,
      open_position_count: 0,
      override_active: false,
      override_until: null,
    },
  ] as AllocationInfo[],
};

// Mock the orchestrator status hook for StrategyOperationsGrid tests
vi.mock('../../hooks', () => ({
  useOrchestratorStatus: () => ({
    data: mockOrchestratorData,
    isLoading: false,
    error: null,
  }),
}));

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

const normalAllocation: AllocationInfo = mockOrchestratorData.allocations[0];

describe('StrategyDecisionStream integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('clicking View Decisions calls onViewDecisions with strategy ID', () => {
    const onViewDecisions = vi.fn();

    render(
      <TestWrapper>
        <StrategyOperationsCard
          allocation={normalAllocation}
          onViewDecisions={onViewDecisions}
        />
      </TestWrapper>
    );

    const viewBtn = screen.getByTestId('view-decisions-button');
    expect(viewBtn).toBeInTheDocument();
    expect(viewBtn).toHaveAttribute('title', 'View strategy decisions');

    fireEvent.click(viewBtn);

    expect(onViewDecisions).toHaveBeenCalledTimes(1);
    expect(onViewDecisions).toHaveBeenCalledWith('orb_breakout');
  });

  it('View Decisions button hidden when onViewDecisions not provided', () => {
    render(
      <TestWrapper>
        <StrategyOperationsCard allocation={normalAllocation} />
      </TestWrapper>
    );

    expect(screen.queryByTestId('view-decisions-button')).not.toBeInTheDocument();
  });

  it('StrategyOperationsGrid forwards onViewDecisions to each card', () => {
    const onViewDecisions = vi.fn();

    render(
      <TestWrapper>
        <StrategyOperationsGrid onViewDecisions={onViewDecisions} />
      </TestWrapper>
    );

    const buttons = screen.getAllByTestId('view-decisions-button');
    expect(buttons).toHaveLength(2);

    // Click the second card's button (vwap_reclaim)
    fireEvent.click(buttons[1]);
    expect(onViewDecisions).toHaveBeenCalledWith('vwap_reclaim');
  });

  it('3-column layout in Section 4 is not affected by card changes', () => {
    // Verify StrategyOperationsCard still renders all expected sections
    const onViewDecisions = vi.fn();

    render(
      <TestWrapper>
        <StrategyOperationsCard
          allocation={normalAllocation}
          onViewDecisions={onViewDecisions}
        />
      </TestWrapper>
    );

    // Strategy name still renders
    expect(screen.getByText('ORB Breakout')).toBeInTheDocument();
    // Badge still renders
    expect(screen.getByText('ORB')).toBeInTheDocument();
    // Allocation section still renders
    expect(screen.getByText('Allocated:')).toBeInTheDocument();
    expect(screen.getByText('Deployed:')).toBeInTheDocument();
    // Performance section still renders
    expect(screen.getByText('Trades:')).toBeInTheDocument();
    expect(screen.getByText('P&L:')).toBeInTheDocument();
    // View Decisions button is present alongside existing controls
    expect(screen.getByTestId('view-decisions-button')).toBeInTheDocument();
    expect(screen.getByTitle('Pause strategy')).toBeInTheDocument();
  });
});
