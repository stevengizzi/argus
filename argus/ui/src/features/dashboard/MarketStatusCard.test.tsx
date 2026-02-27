/**
 * Tests for MarketStatusCard component.
 *
 * Sprint 21d Code Review — Merged Market Status + Market Regime card.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarketStatusCard } from './MarketStatusCard';
import type { AccountResponse, HealthResponse } from '../../api/types';

// Mock hooks
const mockUseAccount = vi.fn();
vi.mock('../../hooks/useAccount', () => ({
  useAccount: () => mockUseAccount(),
}));

const mockUseHealth = vi.fn();
vi.mock('../../hooks/useHealth', () => ({
  useHealth: () => mockUseHealth(),
}));

const mockUseOrchestratorStatus = vi.fn();
vi.mock('../../hooks', () => ({
  useOrchestratorStatus: () => mockUseOrchestratorStatus(),
}));

const mockAccountData: AccountResponse = {
  equity: 100000,
  cash: 50000,
  buying_power: 75000,
  daily_pnl: 500.0,
  daily_pnl_pct: 0.5,
  open_positions_count: 3,
  daily_trades_count: 5,
  market_status: 'open',
  broker_source: 'alpaca',
  data_source: 'alpaca',
  timestamp: '2026-02-28T10:30:00Z',
};

const mockHealthData: HealthResponse = {
  status: 'healthy',
  paper_mode: true,
  components: [],
  uptime_seconds: 3600,
  timestamp: '2026-02-28T10:30:00Z',
};

const mockOrchestratorData = {
  regime: 'bullish_trending',
  regime_updated_at: '2026-02-28T10:15:00Z',
  allocations: [],
  session_phase: 'active_trading',
  pre_market_complete: true,
};

describe('MarketStatusCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Market Status header', () => {
    mockUseAccount.mockReturnValue({
      data: mockAccountData,
      isLoading: false,
    });
    mockUseHealth.mockReturnValue({
      data: mockHealthData,
      isLoading: false,
    });
    mockUseOrchestratorStatus.mockReturnValue({
      data: mockOrchestratorData,
      isLoading: false,
    });

    render(<MarketStatusCard />);

    expect(screen.getByText('Market Status')).toBeInTheDocument();
  });

  it('renders OPEN status with status dot', () => {
    mockUseAccount.mockReturnValue({
      data: { ...mockAccountData, market_status: 'open' },
      isLoading: false,
    });
    mockUseHealth.mockReturnValue({
      data: mockHealthData,
      isLoading: false,
    });
    mockUseOrchestratorStatus.mockReturnValue({
      data: mockOrchestratorData,
      isLoading: false,
    });

    render(<MarketStatusCard />);

    expect(screen.getByText('OPEN')).toBeInTheDocument();
  });

  it('renders PRE-MKT status for pre_market', () => {
    mockUseAccount.mockReturnValue({
      data: { ...mockAccountData, market_status: 'pre_market' },
      isLoading: false,
    });
    mockUseHealth.mockReturnValue({
      data: mockHealthData,
      isLoading: false,
    });
    mockUseOrchestratorStatus.mockReturnValue({
      data: mockOrchestratorData,
      isLoading: false,
    });

    render(<MarketStatusCard />);

    expect(screen.getByText('PRE-MKT')).toBeInTheDocument();
  });

  it('renders PAPER badge when in paper mode', () => {
    mockUseAccount.mockReturnValue({
      data: mockAccountData,
      isLoading: false,
    });
    mockUseHealth.mockReturnValue({
      data: { ...mockHealthData, paper_mode: true },
      isLoading: false,
    });
    mockUseOrchestratorStatus.mockReturnValue({
      data: mockOrchestratorData,
      isLoading: false,
    });

    render(<MarketStatusCard />);

    expect(screen.getByText('PAPER')).toBeInTheDocument();
  });

  it('renders regime badge with description', () => {
    mockUseAccount.mockReturnValue({
      data: mockAccountData,
      isLoading: false,
    });
    mockUseHealth.mockReturnValue({
      data: mockHealthData,
      isLoading: false,
    });
    mockUseOrchestratorStatus.mockReturnValue({
      data: { ...mockOrchestratorData, regime: 'bullish_trending' },
      isLoading: false,
    });

    render(<MarketStatusCard />);

    // Should show regime description
    expect(screen.getByText('Strong upward momentum')).toBeInTheDocument();
  });

  it('renders loading skeleton when data is loading', () => {
    mockUseAccount.mockReturnValue({
      data: null,
      isLoading: true,
    });
    mockUseHealth.mockReturnValue({
      data: null,
      isLoading: true,
    });
    mockUseOrchestratorStatus.mockReturnValue({
      data: null,
      isLoading: true,
    });

    const { container } = render(<MarketStatusCard />);

    // Check for skeleton animation
    const pulsingElements = container.querySelectorAll('.animate-pulse');
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  it('renders fallback message when regime is not available', () => {
    mockUseAccount.mockReturnValue({
      data: mockAccountData,
      isLoading: false,
    });
    mockUseHealth.mockReturnValue({
      data: mockHealthData,
      isLoading: false,
    });
    mockUseOrchestratorStatus.mockReturnValue({
      data: { ...mockOrchestratorData, regime: null },
      isLoading: false,
    });

    render(<MarketStatusCard />);

    expect(screen.getByText(/Regime data available during market hours/i)).toBeInTheDocument();
  });
});
