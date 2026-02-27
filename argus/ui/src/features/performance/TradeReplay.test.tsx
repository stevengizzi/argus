/**
 * TradeReplay component tests.
 *
 * Sprint 21d Session 10: Animated trade replay with candlestick playback.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TradeReplay } from './TradeReplay';

// Mock the hooks
vi.mock('../../hooks/useTradeReplay', () => ({
  useTradeReplay: vi.fn(),
}));

vi.mock('../../hooks/useTrades', () => ({
  useTrades: vi.fn(),
}));

// Mock the strategyConfig utility
vi.mock('../../utils/strategyConfig', () => ({
  getStrategyDisplay: vi.fn((id: string) => {
    const displays: Record<string, { name: string }> = {
      orb_breakout: { name: 'ORB Breakout' },
      vwap_reclaim: { name: 'VWAP Reclaim' },
    };
    return displays[id] || { name: id };
  }),
}));

// Mock lightweight-charts (doesn't work in jsdom)
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => ({
      setData: vi.fn(),
      createPriceLine: vi.fn(),
      removePriceLine: vi.fn(),
      priceLines: vi.fn(() => []),
    })),
    applyOptions: vi.fn(),
    timeScale: vi.fn(() => ({
      fitContent: vi.fn(),
    })),
    remove: vi.fn(),
  })),
  createSeriesMarkers: vi.fn(() => ({
    setMarkers: vi.fn(),
    markers: vi.fn(() => []),
  })),
  CandlestickSeries: {},
  LineSeries: {},
}));

// Mock ResizeObserver
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

import { useTradeReplay } from '../../hooks/useTradeReplay';
import { useTrades } from '../../hooks/useTrades';

const mockTrades = [
  {
    id: 'trade-1',
    strategy_id: 'strat_orb_breakout',
    symbol: 'AAPL',
    side: 'buy',
    entry_price: 150.0,
    entry_time: '2026-02-27T09:45:00Z',
    exit_price: 153.0,
    exit_time: '2026-02-27T10:30:00Z',
    shares: 100,
    pnl_dollars: 300,
    pnl_r_multiple: 2.0,
    exit_reason: 'target_1',
    hold_duration_seconds: 2700,
    commission: 1.0,
    market_regime: 'bullish_trending',
  },
  {
    id: 'trade-2',
    strategy_id: 'strat_vwap_reclaim',
    symbol: 'NVDA',
    side: 'buy',
    entry_price: 800.0,
    entry_time: '2026-02-27T11:00:00Z',
    exit_price: 795.0,
    exit_time: '2026-02-27T11:45:00Z',
    shares: 50,
    pnl_dollars: -250,
    pnl_r_multiple: -0.5,
    exit_reason: 'stop_loss',
    hold_duration_seconds: 2700,
    commission: 1.0,
    market_regime: 'neutral',
  },
];

const mockReplayData = {
  trade: mockTrades[0],
  bars: [
    { timestamp: '2026-02-27T09:30:00Z', open: 149.0, high: 149.5, low: 148.8, close: 149.2, volume: 10000 },
    { timestamp: '2026-02-27T09:31:00Z', open: 149.2, high: 149.8, low: 149.0, close: 149.5, volume: 12000 },
    { timestamp: '2026-02-27T09:32:00Z', open: 149.5, high: 150.2, low: 149.4, close: 150.0, volume: 15000 },
    { timestamp: '2026-02-27T09:33:00Z', open: 150.0, high: 150.5, low: 149.8, close: 150.3, volume: 8000 },
    { timestamp: '2026-02-27T09:34:00Z', open: 150.3, high: 151.0, low: 150.2, close: 150.8, volume: 11000 },
  ],
  entry_bar_index: 2,
  exit_bar_index: 4,
  vwap: [149.1, 149.2, 149.5, 149.8, 150.0],
  timestamp: '2026-02-28T12:00:00Z',
};

describe('TradeReplay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders chart container and playback controls when trade is selected', () => {
    vi.mocked(useTrades).mockReturnValue({
      data: { trades: mockTrades, total_count: 2, limit: 50, offset: 0, timestamp: '' },
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useTrades>);

    vi.mocked(useTradeReplay).mockReturnValue({
      data: mockReplayData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useTradeReplay>);

    render(<TradeReplay initialTradeId="trade-1" />);

    // Should show the title
    expect(screen.getByText('Trade Replay')).toBeInTheDocument();

    // Should show playback controls
    expect(screen.getByTitle('Play')).toBeInTheDocument();
    expect(screen.getByTitle('Reset')).toBeInTheDocument();
    expect(screen.getByTitle('Step back')).toBeInTheDocument();
    expect(screen.getByTitle('Step forward')).toBeInTheDocument();

    // Should show speed buttons
    expect(screen.getByText('1x')).toBeInTheDocument();
    expect(screen.getByText('2x')).toBeInTheDocument();
    expect(screen.getByText('5x')).toBeInTheDocument();
    expect(screen.getByText('10x')).toBeInTheDocument();

    // Should show bar counter
    expect(screen.getByText('1 / 5')).toBeInTheDocument();

    // Should show info panel with trade details
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('buy')).toBeInTheDocument();
  });

  it('shows prompt when no trade is selected', () => {
    vi.mocked(useTrades).mockReturnValue({
      data: { trades: mockTrades, total_count: 2, limit: 50, offset: 0, timestamp: '' },
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useTrades>);

    vi.mocked(useTradeReplay).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useTradeReplay>);

    render(<TradeReplay />);

    expect(screen.getByText('Select a trade to replay')).toBeInTheDocument();
  });

  it('toggles play/pause state', () => {
    vi.mocked(useTrades).mockReturnValue({
      data: { trades: mockTrades, total_count: 2, limit: 50, offset: 0, timestamp: '' },
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useTrades>);

    vi.mocked(useTradeReplay).mockReturnValue({
      data: mockReplayData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useTradeReplay>);

    render(<TradeReplay initialTradeId="trade-1" />);

    // Should start with play button
    const playButton = screen.getByTitle('Play');
    expect(playButton).toBeInTheDocument();

    // Click play
    fireEvent.click(playButton);

    // Should now show pause button
    expect(screen.getByTitle('Pause')).toBeInTheDocument();

    // Click pause
    fireEvent.click(screen.getByTitle('Pause'));

    // Should show play button again
    expect(screen.getByTitle('Play')).toBeInTheDocument();
  });

  it('changes speed when speed button is clicked', () => {
    vi.mocked(useTrades).mockReturnValue({
      data: { trades: mockTrades, total_count: 2, limit: 50, offset: 0, timestamp: '' },
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useTrades>);

    vi.mocked(useTradeReplay).mockReturnValue({
      data: mockReplayData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useTradeReplay>);

    render(<TradeReplay initialTradeId="trade-1" />);

    // 1x should be highlighted by default (has bg-argus-accent class)
    const speed1xButton = screen.getByText('1x');
    expect(speed1xButton).toHaveClass('bg-argus-accent');

    // Click 5x
    fireEvent.click(screen.getByText('5x'));

    // 5x should now be highlighted
    expect(screen.getByText('5x')).toHaveClass('bg-argus-accent');
    // 1x should no longer be highlighted
    expect(speed1xButton).not.toHaveClass('bg-argus-accent');
  });

  it('renders trade selector with options', () => {
    vi.mocked(useTrades).mockReturnValue({
      data: { trades: mockTrades, total_count: 2, limit: 50, offset: 0, timestamp: '' },
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useTrades>);

    vi.mocked(useTradeReplay).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useTradeReplay>);

    render(<TradeReplay />);

    // Should show trade selector
    const selectButton = screen.getByText('Select a trade...');
    expect(selectButton).toBeInTheDocument();

    // Click to open dropdown
    fireEvent.click(selectButton);

    // Should show trade options
    expect(screen.getByText(/AAPL buy/)).toBeInTheDocument();
    expect(screen.getByText(/NVDA buy/)).toBeInTheDocument();
  });
});
