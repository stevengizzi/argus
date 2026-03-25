/**
 * Tests for StrategyOperationsCard component.
 *
 * Sprint 21b, Session 8.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrategyOperationsCard } from './StrategyOperationsCard';
import type { AllocationInfo } from '../../api/types';

// Mock the hooks
vi.mock('../../hooks/useControls', () => ({
  usePauseStrategy: () => ({ mutate: vi.fn(), isPending: false }),
  useResumeStrategy: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock('../../stores/orchestratorUI', () => ({
  useOrchestratorUI: () => vi.fn(),
}));

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

// Wrapper component with providers
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

// Non-throttled allocation
const normalAllocation: AllocationInfo = {
  strategy_id: 'orb_breakout',
  allocation_pct: 25,
  allocation_dollars: 10000,
  throttle_action: 'none',
  eligible: true,
  reason: '',
  deployed_capital: 5000,
  deployed_pct: 12.5,
  is_throttled: false,
  operating_window: {
    earliest_entry: '09:35',
    latest_entry: '10:05',
    force_close: '10:30',
  },
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
};

// Throttled allocation
const throttledAllocation: AllocationInfo = {
  ...normalAllocation,
  strategy_id: 'vwap_reclaim',
  throttle_action: 'reduce',
  is_throttled: true,
  reason: 'Consecutive losses exceeded threshold',
  consecutive_losses: 4,
  rolling_sharpe: -0.8,
  drawdown_pct: 12.0,
  daily_pnl: -200,
};

// Suspended allocation (circuit breaker — not throttled)
const suspendedAllocation: AllocationInfo = {
  ...normalAllocation,
  strategy_id: 'orb_scalp',
  is_active: false,
  throttle_action: 'none',
  is_throttled: false,
  reason: '5 consecutive losses — circuit breaker triggered',
  consecutive_losses: 5,
};

// Suspended allocation with empty reason
const suspendedNoReasonAllocation: AllocationInfo = {
  ...normalAllocation,
  strategy_id: 'orb_scalp',
  is_active: false,
  throttle_action: 'none',
  is_throttled: false,
  reason: '',
  consecutive_losses: 5,
};

// Suspended via throttle (throttle_action='suspend') — should show throttle, not suspension
const throttleSuspendedAllocation: AllocationInfo = {
  ...normalAllocation,
  strategy_id: 'vwap_reclaim',
  is_active: false,
  throttle_action: 'suspend',
  is_throttled: true,
  reason: 'PerformanceThrottler suspended strategy',
  consecutive_losses: 6,
  rolling_sharpe: -1.2,
  drawdown_pct: 15.0,
};

describe('StrategyOperationsCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders strategy name and badge', () => {
    render(
      <TestWrapper>
        <StrategyOperationsCard allocation={normalAllocation} />
      </TestWrapper>
    );

    // Check for strategy name
    expect(screen.getByText('ORB Breakout')).toBeInTheDocument();

    // Check for badge (ORB)
    expect(screen.getByText('ORB')).toBeInTheDocument();
  });

  it('shows throttle section when throttle_action is reduce', () => {
    render(
      <TestWrapper>
        <StrategyOperationsCard allocation={throttledAllocation} />
      </TestWrapper>
    );

    // Should show throttle reason
    expect(screen.getByText(/Consecutive losses exceeded threshold/)).toBeInTheDocument();

    // Should show Override button
    expect(screen.getByText('Override Throttle')).toBeInTheDocument();

    // Should show throttle metrics (Losses, Sharpe, DD)
    expect(screen.getByText(/Losses:/)).toBeInTheDocument();
    expect(screen.getByText(/Sharpe:/)).toBeInTheDocument();
    expect(screen.getByText(/DD:/)).toBeInTheDocument();
  });

  it('shows suspension section when inactive and not throttled', () => {
    render(
      <TestWrapper>
        <StrategyOperationsCard allocation={suspendedAllocation} />
      </TestWrapper>
    );

    // Should show suspension section with badge
    const section = screen.getByTestId('suspension-section');
    expect(section).toBeInTheDocument();
    expect(section).toHaveTextContent('Suspended');

    // Should show reason
    expect(screen.getByTestId('suspension-reason')).toHaveTextContent(
      '5 consecutive losses — circuit breaker triggered'
    );

    // Should NOT show throttle Override button
    expect(screen.queryByText('Override Throttle')).not.toBeInTheDocument();
  });

  it('hides suspension section when active', () => {
    render(
      <TestWrapper>
        <StrategyOperationsCard allocation={normalAllocation} />
      </TestWrapper>
    );

    expect(screen.queryByTestId('suspension-section')).not.toBeInTheDocument();
  });

  it('shows throttle not suspension when throttle_action is suspend', () => {
    render(
      <TestWrapper>
        <StrategyOperationsCard allocation={throttleSuspendedAllocation} />
      </TestWrapper>
    );

    // Throttle section should appear (with Override button)
    expect(screen.getByText('Override Throttle')).toBeInTheDocument();

    // Suspension section should NOT appear
    expect(screen.queryByTestId('suspension-section')).not.toBeInTheDocument();
  });

  it('shows default reason when suspension reason is empty', () => {
    render(
      <TestWrapper>
        <StrategyOperationsCard allocation={suspendedNoReasonAllocation} />
      </TestWrapper>
    );

    expect(screen.getByTestId('suspension-reason')).toHaveTextContent(
      'Circuit breaker — consecutive losses'
    );
  });

  it('shows suspended status in operating window when inactive', () => {
    render(
      <TestWrapper>
        <StrategyOperationsCard allocation={suspendedAllocation} />
      </TestWrapper>
    );

    const windowStatus = screen.getByTestId('window-status');
    expect(windowStatus).toHaveTextContent('Suspended');
  });

  it('does not show suspended window status when throttled', () => {
    render(
      <TestWrapper>
        <StrategyOperationsCard allocation={throttleSuspendedAllocation} />
      </TestWrapper>
    );

    const windowStatus = screen.getByTestId('window-status');
    expect(windowStatus).not.toHaveTextContent('Suspended');
  });
});
