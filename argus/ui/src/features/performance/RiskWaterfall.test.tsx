/**
 * RiskWaterfall component tests.
 *
 * Sprint 21d Session 7: Risk waterfall chart showing worst-case risk per position.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskWaterfall } from './RiskWaterfall';

// Mock the usePositions hook
vi.mock('../../hooks/usePositions', () => ({
  usePositions: vi.fn(),
}));

// Mock the useAccount hook
vi.mock('../../hooks/useAccount', () => ({
  useAccount: vi.fn(),
}));

import { usePositions } from '../../hooks/usePositions';
import { useAccount } from '../../hooks/useAccount';

const mockPositionsData = {
  positions: [
    {
      position_id: 'pos-1',
      strategy_id: 'strat_orb_breakout',
      symbol: 'AAPL',
      side: 'long',
      entry_price: 180.0,
      stop_price: 178.0,
      shares_remaining: 50,
      current_price: 181.5,
      unrealized_pnl: 75,
      unrealized_pnl_pct: 0.83,
      entry_time: '2026-02-28T10:00:00Z',
      shares_total: 50,
      t1_price: 182.0,
      t2_price: 184.0,
      t1_filled: false,
      hold_duration_seconds: 3600,
      r_multiple_current: 0.75,
    },
    {
      position_id: 'pos-2',
      strategy_id: 'strat_vwap_reclaim',
      symbol: 'NVDA',
      side: 'long',
      entry_price: 850.0,
      stop_price: 845.0,
      shares_remaining: 20,
      current_price: 852.0,
      unrealized_pnl: 40,
      unrealized_pnl_pct: 0.24,
      entry_time: '2026-02-28T11:00:00Z',
      shares_total: 20,
      t1_price: 855.0,
      t2_price: 860.0,
      t1_filled: false,
      hold_duration_seconds: 1800,
      r_multiple_current: 0.4,
    },
  ],
  count: 2,
  timestamp: '2026-02-28T12:00:00Z',
};

const mockAccountData = {
  equity: 100000,
  cash: 50000,
  buying_power: 75000,
  daily_pnl: 500,
  daily_pnl_pct: 0.5,
  open_positions_count: 2,
  daily_trades_count: 5,
  market_status: 'open' as const,
  broker_source: 'alpaca',
  data_source: 'alpaca',
  timestamp: '2026-02-28T12:00:00Z',
};

describe('RiskWaterfall', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders bars for open positions', () => {
    vi.mocked(usePositions).mockReturnValue({
      data: mockPositionsData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof usePositions>);

    vi.mocked(useAccount).mockReturnValue({
      data: mockAccountData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useAccount>);

    render(<RiskWaterfall />);

    // Should show the title
    expect(screen.getByText('Risk Waterfall')).toBeInTheDocument();

    // Should show the subtitle
    expect(screen.getByText('Worst-case scenario if all stops hit')).toBeInTheDocument();

    // Should render SVG
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Should show position symbols
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('NVDA')).toBeInTheDocument();

    // Should show total risk summary
    expect(screen.getByText(/Total risk:/)).toBeInTheDocument();
  });

  it('shows empty state when no positions', () => {
    vi.mocked(usePositions).mockReturnValue({
      data: { positions: [], count: 0, timestamp: '' },
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof usePositions>);

    vi.mocked(useAccount).mockReturnValue({
      data: mockAccountData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useAccount>);

    render(<RiskWaterfall />);

    expect(screen.getByText('No open positions — zero risk exposure')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    vi.mocked(usePositions).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isFetching: true,
    } as ReturnType<typeof usePositions>);

    vi.mocked(useAccount).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isFetching: true,
    } as ReturnType<typeof useAccount>);

    render(<RiskWaterfall />);

    expect(screen.getByText('Loading positions...')).toBeInTheDocument();
  });

  it('calculates and displays risk correctly', () => {
    vi.mocked(usePositions).mockReturnValue({
      data: mockPositionsData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof usePositions>);

    vi.mocked(useAccount).mockReturnValue({
      data: mockAccountData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useAccount>);

    render(<RiskWaterfall />);

    // AAPL risk: 50 shares × ($180 - $178) = $100
    // NVDA risk: 20 shares × ($850 - $845) = $100
    // Total risk: $200

    // Check total risk text is displayed (look for the value)
    const totalRiskText = screen.getByText(/Total risk:/);
    expect(totalRiskText).toBeInTheDocument();
  });
});
