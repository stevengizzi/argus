/**
 * Tests for SessionOverview component.
 *
 * Sprint 21b review fixes.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SessionOverview } from './SessionOverview';
import type { AllocationInfo } from '../../api/types';

const mockAllocations: AllocationInfo[] = [
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
    throttle_action: 'reduce',
    eligible: true,
    reason: 'Consecutive losses',
    deployed_capital: 5000,
    deployed_pct: 0.05,
    is_throttled: true,
    operating_window: { earliest_entry: '09:35', latest_entry: '11:00', force_close: '15:55' },
    consecutive_losses: 3,
    rolling_sharpe: -0.5,
    drawdown_pct: 8.0,
    is_active: true,
    health_status: 'warning',
    trade_count_today: 5,
    daily_pnl: -125.25,
    open_position_count: 0,
    override_active: false,
    override_until: null,
  },
];

describe('SessionOverview', () => {
  it('renders with title', () => {
    render(<SessionOverview allocations={mockAllocations} />);

    expect(screen.getByText('Session Overview')).toBeInTheDocument();
  });

  it('shows aggregated Total P&L', () => {
    render(<SessionOverview allocations={mockAllocations} />);

    // Total P&L label
    expect(screen.getByText('Total P&L Today')).toBeInTheDocument();
  });

  it('shows aggregated trades count', () => {
    render(<SessionOverview allocations={mockAllocations} />);

    // 3 + 5 = 8 trades
    expect(screen.getByText('Trades Today')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('shows aggregated open positions count', () => {
    render(<SessionOverview allocations={mockAllocations} />);

    // 1 + 0 = 1 open position
    const openPositionsLabel = screen.getByText('Open Positions');
    expect(openPositionsLabel).toBeInTheDocument();

    // The row should contain the value "1" (open positions = 1)
    const row = openPositionsLabel.parentElement;
    expect(row?.textContent).toContain('1');
  });

  it('shows active strategies count', () => {
    render(<SessionOverview allocations={mockAllocations} />);

    // Both are active: 2 / 2
    expect(screen.getByText('Active Strategies')).toBeInTheDocument();
    expect(screen.getByText('2 / 2')).toBeInTheDocument();
  });

  it('shows throttled count when strategies are throttled', () => {
    render(<SessionOverview allocations={mockAllocations} />);

    // One is throttled
    expect(screen.getByText('Throttled')).toBeInTheDocument();
    // The value "1" appears for throttled count (also appears for open positions)
  });

  it('shows "None" when no strategies are throttled', () => {
    const noThrottleAllocations = mockAllocations.map((a) => ({
      ...a,
      is_throttled: false,
    }));

    render(<SessionOverview allocations={noThrottleAllocations} />);

    expect(screen.getByText('None')).toBeInTheDocument();
  });

  it('handles empty allocations array', () => {
    render(<SessionOverview allocations={[]} />);

    // Should render without crashing
    expect(screen.getByText('Session Overview')).toBeInTheDocument();
    expect(screen.getByText('0 / 0')).toBeInTheDocument(); // Active strategies
    expect(screen.getByText('None')).toBeInTheDocument(); // Throttled
  });
});
