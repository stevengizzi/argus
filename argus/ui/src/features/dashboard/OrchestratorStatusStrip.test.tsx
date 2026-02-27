/**
 * Tests for OrchestratorStatusStrip component.
 *
 * Sprint 21d Session 4.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { OrchestratorStatusStrip } from './OrchestratorStatusStrip';
import type { OrchestratorStatusResponse } from '../../api/types';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock useOrchestratorStatus hook
const mockUseOrchestratorStatus = vi.fn();
vi.mock('../../hooks', () => ({
  useOrchestratorStatus: () => mockUseOrchestratorStatus(),
}));

// Mock useMediaQuery for responsive tests
vi.mock('../../hooks/useMediaQuery', () => ({
  useMediaQuery: vi.fn(() => false), // Default: not mobile
}));

const mockOrchestratorData: OrchestratorStatusResponse = {
  regime: 'bullish_trending',
  regime_indicators: {
    volatility: 0.15,
    trend_score: 0.25,
    momentum: 0.18,
  },
  regime_updated_at: '2026-02-28T10:00:00Z',
  allocations: [
    {
      strategy_id: 'orb_breakout',
      allocation_pct: 0.25,
      allocation_dollars: 25000,
      throttle_action: 'none',
      eligible: true,
      reason: '',
      deployed_capital: 10000,
      deployed_pct: 0.10,
      is_throttled: false,
      operating_window: { earliest_entry: '09:35', latest_entry: '10:30', force_close: '15:55' },
      consecutive_losses: 0,
      rolling_sharpe: 1.5,
      drawdown_pct: 2.5,
      is_active: true,
      health_status: 'healthy',
      trade_count_today: 3,
      daily_pnl: 450.50,
      open_position_count: 1,
      override_active: false,
      override_until: null,
    },
    {
      strategy_id: 'orb_scalp',
      allocation_pct: 0.25,
      allocation_dollars: 25000,
      throttle_action: 'none',
      eligible: true,
      reason: '',
      deployed_capital: 5000,
      deployed_pct: 0.05,
      is_throttled: false,
      operating_window: { earliest_entry: '09:35', latest_entry: '11:00', force_close: '15:55' },
      consecutive_losses: 1,
      rolling_sharpe: 0.8,
      drawdown_pct: 4.0,
      is_active: true,
      health_status: 'healthy',
      trade_count_today: 5,
      daily_pnl: 125.25,
      open_position_count: 0,
      override_active: false,
      override_until: null,
    },
    {
      strategy_id: 'vwap_reclaim',
      allocation_pct: 0.25,
      allocation_dollars: 25000,
      throttle_action: 'none',
      eligible: true,
      reason: '',
      deployed_capital: 8000,
      deployed_pct: 0.08,
      is_throttled: false,
      operating_window: null,
      consecutive_losses: 0,
      rolling_sharpe: 1.2,
      drawdown_pct: 3.0,
      is_active: false, // Inactive
      health_status: 'healthy',
      trade_count_today: 0,
      daily_pnl: 0,
      open_position_count: 0,
      override_active: false,
      override_until: null,
    },
  ],
  cash_reserve_pct: 0.20,
  total_deployed_pct: 0.23,
  next_regime_check: '2026-02-28T10:30:00Z',
  total_deployed_capital: 23000,
  total_equity: 100000,
  timestamp: '2026-02-28T10:15:00Z',
  session_phase: 'active',
  pre_market_complete: true,
  pre_market_completed_at: '2026-02-28T09:30:00Z',
};

function renderComponent() {
  return render(
    <MemoryRouter>
      <OrchestratorStatusStrip />
    </MemoryRouter>
  );
}

describe('OrchestratorStatusStrip', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with mock data showing strategy count and deployed capital', () => {
    mockUseOrchestratorStatus.mockReturnValue({
      data: mockOrchestratorData,
      isLoading: false,
      isError: false,
    });

    renderComponent();

    // Check strategy count (2 active out of 3)
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText(/strategies active/)).toBeInTheDocument();

    // Check deployed capital
    expect(screen.getByText('$23,000')).toBeInTheDocument();

    // Check regime badge
    expect(screen.getByText('Bullish')).toBeInTheDocument();
  });

  it('shows fallback state when orchestrator is unavailable', () => {
    mockUseOrchestratorStatus.mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
    });

    renderComponent();

    expect(screen.getByText(/Orchestrator offline/)).toBeInTheDocument();
  });

  it('navigates to orchestrator page on click', () => {
    mockUseOrchestratorStatus.mockReturnValue({
      data: mockOrchestratorData,
      isLoading: false,
      isError: false,
    });

    renderComponent();

    const strip = screen.getByTestId('orchestrator-status-strip');
    fireEvent.click(strip);

    expect(mockNavigate).toHaveBeenCalledWith('/orchestrator');
  });
});
