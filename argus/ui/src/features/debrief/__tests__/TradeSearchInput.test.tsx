/**
 * Tests for TradeSearchInput component.
 *
 * Sprint 21c, Session 10.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// Mock the API client - inline data to avoid hoisting issues
vi.mock('../../../api/client', () => {
  const mockTradesData = [
    {
      id: 'trade-001',
      strategy_id: 'orb_breakout',
      symbol: 'TSLA',
      side: 'long',
      entry_price: 250.00,
      entry_time: '2026-02-27T09:45:00Z',
      exit_price: 255.00,
      exit_time: '2026-02-27T10:15:00Z',
      shares: 50,
      pnl_dollars: 250.00,
      pnl_r_multiple: 1.5,
      exit_reason: 'target_1',
      hold_duration_seconds: 1800,
      commission: 0.50,
      market_regime: 'trending',
    },
    {
      id: 'trade-002',
      strategy_id: 'vwap_reclaim',
      symbol: 'NVDA',
      side: 'long',
      entry_price: 850.00,
      entry_time: '2026-02-27T11:00:00Z',
      exit_price: 840.00,
      exit_time: '2026-02-27T11:30:00Z',
      shares: 20,
      pnl_dollars: -200.00,
      pnl_r_multiple: -1.0,
      exit_reason: 'stop_loss',
      hold_duration_seconds: 1800,
      commission: 0.40,
      market_regime: 'ranging',
    },
  ];

  return {
    getTrades: vi.fn().mockResolvedValue({
      trades: mockTradesData,
    }),
    getTradesByIds: vi.fn().mockImplementation((ids: string[]) => {
      const trades = mockTradesData.filter((t) => ids.includes(t.id));
      return Promise.resolve({
        trades,
        count: trades.length,
        timestamp: new Date().toISOString(),
      });
    }),
  };
});

// Mock the symbol detail UI store
vi.mock('../../../stores/symbolDetailUI', () => ({
  useSymbolDetailUI: () => ({
    open: vi.fn(),
  }),
}));

// Import after mocking
import { TradeSearchInput } from '../journal/TradeSearchInput';

describe('TradeSearchInput', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders search input', () => {
    const onChange = vi.fn();

    render(<TradeSearchInput linkedTradeIds={[]} onChange={onChange} />);

    expect(screen.getByPlaceholderText('Search trades by symbol...')).toBeInTheDocument();
  });

  it('shows linked trades as chips', async () => {
    const onChange = vi.fn();

    render(
      <TradeSearchInput
        linkedTradeIds={['trade-001', 'trade-002']}
        onChange={onChange}
      />
    );

    // Wait for linked trades to be fetched and displayed
    await waitFor(() => {
      expect(screen.getByText('TSLA')).toBeInTheDocument();
    });

    expect(screen.getByText('NVDA')).toBeInTheDocument();
  });

  it('removes linked trade when X is clicked', async () => {
    const onChange = vi.fn();

    render(
      <TradeSearchInput
        linkedTradeIds={['trade-001', 'trade-002']}
        onChange={onChange}
      />
    );

    // Wait for linked trades to be displayed
    await waitFor(() => {
      expect(screen.getByText('TSLA')).toBeInTheDocument();
    });

    // Find and click the remove button for one of the trades
    const removeButtons = screen.getAllByRole('button', { name: /Remove/i });
    fireEvent.click(removeButtons[0]);

    // onChange should be called with that trade removed
    expect(onChange).toHaveBeenCalledWith(['trade-002']);
  });

  it('renders with empty state when no linked trades', () => {
    const onChange = vi.fn();

    render(<TradeSearchInput linkedTradeIds={[]} onChange={onChange} />);

    // Should just have the search input, no chips
    expect(screen.getByPlaceholderText('Search trades by symbol...')).toBeInTheDocument();
    expect(screen.queryByText('TSLA')).not.toBeInTheDocument();
    expect(screen.queryByText('NVDA')).not.toBeInTheDocument();
  });
});
