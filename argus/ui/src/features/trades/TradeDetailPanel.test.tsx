/**
 * Tests for TradeDetailPanel component.
 *
 * Sprint 21.5.1, Session 3.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TradeDetailPanel } from './TradeDetailPanel';
import type { Trade } from '../../api/types';

// Mock the symbol detail store
vi.mock('../../stores/symbolDetailUI', () => ({
  useSymbolDetailUI: () => ({ open: vi.fn() }),
}));

// Mock the TradeChart component since it makes API calls
vi.mock('../../components/TradeChart', () => ({
  TradeChart: () => <div data-testid="mock-trade-chart">Trade Chart</div>,
}));

const mockTrade: Trade = {
  id: 'trade-001',
  strategy_id: 'strat_orb_breakout',
  symbol: 'TSLA',
  side: 'long',
  entry_price: 250.0,
  entry_time: '2026-02-25T14:35:00Z',
  exit_price: 255.0,
  exit_time: '2026-02-25T15:00:00Z',
  shares: 100,
  pnl_dollars: 500.0,
  pnl_r_multiple: 2.5,
  exit_reason: 'target_1',
  hold_duration_seconds: 1500,
  commission: 1.0,
  market_regime: 'bullish',
  stop_price: 248.0,
  target_prices: [254.0, 258.0],
};

describe('TradeDetailPanel', () => {
  it('renders nothing when trade is null', () => {
    const { container } = render(<TradeDetailPanel trade={null} onClose={() => {}} />);

    // Panel should not show trade content when trade is null
    expect(screen.queryByText('TSLA')).not.toBeInTheDocument();
  });

  it('renders trade details when trade is provided', () => {
    render(<TradeDetailPanel trade={mockTrade} onClose={() => {}} />);

    // Should show the symbol
    expect(screen.getByText('TSLA')).toBeInTheDocument();
    // Should show the strategy
    expect(screen.getByText('strat_orb_breakout')).toBeInTheDocument();
  });

  it('displays price levels section with stop and target prices', () => {
    render(<TradeDetailPanel trade={mockTrade} onClose={() => {}} />);

    // Should show the Price Levels header
    expect(screen.getByText('Price Levels')).toBeInTheDocument();

    // Should show Stop label in the price levels section
    expect(screen.getByText('Stop')).toBeInTheDocument();

    // T1 appears twice - once in price levels, once in exit reason badge
    // Verify at least one T1 element exists in the price levels section
    const t1Elements = screen.getAllByText('T1');
    expect(t1Elements.length).toBeGreaterThanOrEqual(1);

    // Should show T2 label (since target_prices[1] exists and > 0)
    expect(screen.getByText('T2')).toBeInTheDocument();

    // Should show formatted price values (e.g., $248.00, $254.00, $258.00)
    // Using regex to find the price text content
    expect(screen.getByText(/248\.00/)).toBeInTheDocument();
    expect(screen.getByText(/254\.00/)).toBeInTheDocument();
    expect(screen.getByText(/258\.00/)).toBeInTheDocument();
  });

  it('shows dashes for missing price levels', () => {
    const tradeWithoutLevels: Trade = {
      ...mockTrade,
      stop_price: undefined,
      target_prices: undefined,
    };

    render(<TradeDetailPanel trade={tradeWithoutLevels} onClose={() => {}} />);

    // Should show dash for stop when not provided
    const stopSection = screen.getByText('Stop').closest('div')?.parentElement;
    expect(stopSection).toBeInTheDocument();
    // The dash character should appear in place of the price
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  it('shows exit reason badge and explanation', () => {
    render(<TradeDetailPanel trade={mockTrade} onClose={() => {}} />);

    // Exit reason section should exist
    expect(screen.getByText('Exit Reason')).toBeInTheDocument();

    // Should show the T1 badge for target_1 exit (may appear multiple times)
    const t1Elements = screen.getAllByText('T1');
    expect(t1Elements.length).toBeGreaterThanOrEqual(1);

    // Should show the explanation text
    expect(screen.getByText(/Target 1 hit/)).toBeInTheDocument();
  });

  it('displays P&L with R-multiple', () => {
    render(<TradeDetailPanel trade={mockTrade} onClose={() => {}} />);

    // Should show P&L value (formatted as currency)
    expect(screen.getByText(/\+\$500\.00/)).toBeInTheDocument();

    // Should show R-multiple value (format is "+2.50R")
    expect(screen.getByText(/\+2\.50R/)).toBeInTheDocument();

    // Should show "R-multiple" label (may have whitespace)
    expect(screen.getByText(/R-multiple/)).toBeInTheDocument();
  });
});
