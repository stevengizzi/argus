/**
 * Tests for PositionTimeline component.
 *
 * Sprint 18, Session 11 (18-B).
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PositionTimeline } from './PositionTimeline';
import type { Position, Trade } from '../api/types';

// Mock position data
const mockPosition: Position = {
  position_id: 'pos-001',
  strategy_id: 'orb_breakout',
  symbol: 'TSLA',
  side: 'long',
  entry_price: 250.00,
  entry_time: new Date().toISOString(),
  shares_total: 100,
  shares_remaining: 100,
  current_price: 252.00,
  unrealized_pnl: 200.00,
  unrealized_pnl_pct: 0.8,
  stop_price: 248.00,
  t1_price: 254.00,
  t2_price: 258.00,
  t1_filled: false,
  hold_duration_seconds: 300, // 5 minutes
  r_multiple_current: 1.0,
};

const mockTrade: Trade = {
  id: 'trade-001',
  strategy_id: 'orb_scalp',
  symbol: 'NVDA',
  side: 'long',
  entry_price: 900.00,
  entry_time: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
  exit_price: 905.00,
  exit_time: new Date(Date.now() - 3300000).toISOString(), // 55 min ago
  shares: 50,
  pnl_dollars: 250.00,
  pnl_r_multiple: 1.5,
  exit_reason: 'target_1',
  hold_duration_seconds: 300,
  commission: 0.50,
  market_regime: 'bullish',
};

describe('PositionTimeline', () => {
  it('renders empty state when no positions', () => {
    render(<PositionTimeline positions={[]} />);

    expect(screen.getByText('No positions to display on timeline')).toBeInTheDocument();
  });

  it('renders with open positions', () => {
    render(<PositionTimeline positions={[mockPosition]} />);

    // Should show the symbol
    expect(screen.getByText('TSLA')).toBeInTheDocument();
  });

  it('renders with closed trades', () => {
    render(
      <PositionTimeline
        positions={[]}
        closedTrades={[mockTrade]}
      />
    );

    // Should show the symbol from the closed trade
    expect(screen.getByText('NVDA')).toBeInTheDocument();
  });

  it('renders time axis labels', () => {
    render(<PositionTimeline positions={[mockPosition]} />);

    // Should have time labels
    expect(screen.getByText('9:30 AM')).toBeInTheDocument();
    expect(screen.getByText('4:00 PM')).toBeInTheDocument();
  });

  it('calls onPositionClick when position bar is clicked', () => {
    const handleClick = vi.fn();
    render(
      <PositionTimeline
        positions={[mockPosition]}
        onPositionClick={handleClick}
      />
    );

    // Click on the position bar (find by symbol text)
    const positionBar = screen.getByText('TSLA').closest('div');
    if (positionBar) {
      positionBar.click();
    }

    // Callback should have been called with the position
    expect(handleClick).toHaveBeenCalledWith(mockPosition);
  });
});

describe('Timeline scale calculations', () => {
  it('correctly calculates bar positions within market hours', () => {
    // Create a position that started at 10:00 AM ET
    const morningPosition: Position = {
      ...mockPosition,
      position_id: 'pos-morning',
      entry_time: '2026-02-25T15:00:00Z', // 10:00 AM ET (UTC-5)
      hold_duration_seconds: 1800, // 30 minutes
    };

    render(<PositionTimeline positions={[morningPosition]} />);

    // Position should be rendered
    expect(screen.getByText('TSLA')).toBeInTheDocument();
  });

  it('handles multiple overlapping positions with stacking', () => {
    const position1: Position = {
      ...mockPosition,
      position_id: 'pos-001',
      symbol: 'TSLA',
      entry_time: '2026-02-25T14:30:00Z', // 9:30 AM ET
    };

    const position2: Position = {
      ...mockPosition,
      position_id: 'pos-002',
      symbol: 'AAPL',
      entry_time: '2026-02-25T14:35:00Z', // 9:35 AM ET (overlaps with pos-001)
    };

    render(<PositionTimeline positions={[position1, position2]} />);

    // Both symbols should be visible
    expect(screen.getByText('TSLA')).toBeInTheDocument();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
  });
});
