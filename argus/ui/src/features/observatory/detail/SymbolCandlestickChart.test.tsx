/**
 * Tests for SymbolCandlestickChart and useSymbolDetail hook.
 *
 * Sprint 25, Session 4b.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { SymbolCandlestickChart } from './SymbolCandlestickChart';
import { useSymbolDetail } from '../hooks/useSymbolDetail';
import type { BarData } from '../../../api/types';

// Mock lightweight-charts
const mockSetData = vi.fn();
const mockFitContent = vi.fn();
const mockRemove = vi.fn();
const mockApplyOptions = vi.fn();
const mockAddSeries = vi.fn(() => ({
  setData: mockSetData,
}));
const mockTimeScale = vi.fn(() => ({ fitContent: mockFitContent }));

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addSeries: mockAddSeries,
    timeScale: mockTimeScale,
    remove: mockRemove,
    applyOptions: mockApplyOptions,
  })),
  CandlestickSeries: 'CandlestickSeries',
  LineStyle: { Solid: 0, Dotted: 1, Dashed: 2, LargeDashed: 3 },
}));

// Mock API client
const mockGetSymbolJourney = vi.fn().mockResolvedValue({
  symbol: 'AAPL',
  events: [],
  count: 0,
  date: '2026-03-17',
  timestamp: '2026-03-17T14:30:00Z',
});
const mockGetQualityScore = vi.fn().mockResolvedValue({
  symbol: 'AAPL',
  strategy_id: 'orb_breakout',
  score: 7.5,
  grade: 'B',
  risk_tier: 'normal',
  components: { cq: 0, ht: 0, rt: 0, vp: 0, hm: 0, ra: 0 },
  scored_at: '2026-03-17T14:30:00Z',
  outcome_realized_pnl: null,
  outcome_r_multiple: null,
});
const mockGetCatalystsBySymbol = vi.fn().mockResolvedValue({
  catalysts: [],
  count: 0,
  symbol: 'AAPL',
});
const mockFetchSymbolBars = vi.fn().mockResolvedValue({
  symbol: 'AAPL',
  timeframe: '1m',
  bars: [],
  count: 0,
});

vi.mock('../../../api/client', () => ({
  getSymbolJourney: (...args: unknown[]) => mockGetSymbolJourney(...args),
  getQualityScore: (...args: unknown[]) => mockGetQualityScore(...args),
  getCatalystsBySymbol: (...args: unknown[]) => mockGetCatalystsBySymbol(...args),
  fetchSymbolBars: (...args: unknown[]) => mockFetchSymbolBars(...args),
}));

const SAMPLE_BARS: BarData[] = [
  { timestamp: '2026-03-17T14:30:00Z', open: 150, high: 152, low: 149, close: 151, volume: 10000 },
  { timestamp: '2026-03-17T14:31:00Z', open: 151, high: 153, low: 150, close: 152, volume: 8000 },
  { timestamp: '2026-03-17T14:32:00Z', open: 152, high: 154, low: 151, close: 153, volume: 12000 },
];

function createQueryWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('SymbolCandlestickChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with candle data', () => {
    render(<SymbolCandlestickChart symbol="AAPL" bars={SAMPLE_BARS} />);

    expect(screen.getByTestId('symbol-candlestick-chart')).toBeInTheDocument();
    // Chart should be created and data set
    expect(mockAddSeries).toHaveBeenCalledOnce();
    expect(mockSetData).toHaveBeenCalledOnce();
    expect(mockSetData.mock.calls[0][0]).toHaveLength(3);
  });

  it('disposes chart on unmount', () => {
    const { unmount } = render(<SymbolCandlestickChart symbol="AAPL" bars={SAMPLE_BARS} />);

    expect(mockRemove).not.toHaveBeenCalled();
    unmount();
    expect(mockRemove).toHaveBeenCalledOnce();
  });

  it('reinitializes chart on symbol change', () => {
    const { rerender } = render(
      <SymbolCandlestickChart symbol="AAPL" bars={SAMPLE_BARS} />
    );

    expect(mockRemove).not.toHaveBeenCalled();

    rerender(<SymbolCandlestickChart symbol="TSLA" bars={SAMPLE_BARS} />);

    // Old chart should be removed, new chart created
    expect(mockRemove).toHaveBeenCalledOnce();
    // addSeries called twice (once per symbol)
    expect(mockAddSeries).toHaveBeenCalledTimes(2);
  });
});

describe('useSymbolDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches data on symbol change', async () => {
    const { result } = renderHook(
      () => useSymbolDetail({ symbol: 'AAPL' }),
      { wrapper: createQueryWrapper() }
    );

    await waitFor(() => {
      expect(result.current.journey).toBeDefined();
    });

    expect(mockGetSymbolJourney).toHaveBeenCalledWith('AAPL', undefined);
    expect(mockGetQualityScore).toHaveBeenCalledWith('AAPL');
    expect(mockGetCatalystsBySymbol).toHaveBeenCalledWith('AAPL', 5);
    expect(mockFetchSymbolBars).toHaveBeenCalledWith('AAPL', 390);
  });

  it('does not fetch when symbol is null', () => {
    renderHook(
      () => useSymbolDetail({ symbol: null }),
      { wrapper: createQueryWrapper() }
    );

    expect(mockGetSymbolJourney).not.toHaveBeenCalled();
    expect(mockGetQualityScore).not.toHaveBeenCalled();
    expect(mockGetCatalystsBySymbol).not.toHaveBeenCalled();
    expect(mockFetchSymbolBars).not.toHaveBeenCalled();
  });

  it('disables polling in debrief mode', async () => {
    const { result } = renderHook(
      () => useSymbolDetail({ symbol: 'AAPL', date: '2026-03-17' }),
      { wrapper: createQueryWrapper() }
    );

    await waitFor(() => {
      expect(result.current.journey).toBeDefined();
    });

    // Debrief should pass date to journey query
    expect(mockGetSymbolJourney).toHaveBeenCalledWith('AAPL', '2026-03-17');
  });
});
