/**
 * Tests for TradeChart component.
 *
 * Sprint 21.5.1, Session 4.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TradeChart } from './TradeChart';

// Mock lightweight-charts
const mockCreatePriceLine = vi.fn();
const mockSetMarkers = vi.fn();
const mockSetData = vi.fn();
const mockFitContent = vi.fn();
const mockAddSeries = vi.fn(() => ({
  setData: mockSetData,
  createPriceLine: mockCreatePriceLine,
}));
const mockTimeScale = vi.fn(() => ({ fitContent: mockFitContent }));
const mockRemove = vi.fn();
const mockApplyOptions = vi.fn();

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addSeries: mockAddSeries,
    timeScale: mockTimeScale,
    remove: mockRemove,
    applyOptions: mockApplyOptions,
    priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
  })),
  createSeriesMarkers: vi.fn(() => ({
    setMarkers: mockSetMarkers,
  })),
  CandlestickSeries: 'CandlestickSeries',
  LineStyle: {
    Solid: 0,
    Dashed: 1,
    Dotted: 2,
  },
}));

// Mock the useTradeChartBars hook
const mockBarsData = {
  symbol: 'TSLA',
  timeframe: '1m',
  bars: [
    { timestamp: '2026-02-25T14:30:00Z', open: 249, high: 251, low: 248, close: 250, volume: 1000 },
    { timestamp: '2026-02-25T14:31:00Z', open: 250, high: 252, low: 249, close: 251, volume: 1500 },
    { timestamp: '2026-02-25T14:32:00Z', open: 251, high: 253, low: 250, close: 252, volume: 1200 },
    { timestamp: '2026-02-25T14:35:00Z', open: 252, high: 254, low: 251, close: 253, volume: 1100 },
    { timestamp: '2026-02-25T14:40:00Z', open: 253, high: 256, low: 253, close: 255, volume: 2000 },
  ],
  count: 5,
};

vi.mock('../hooks/useSymbolBars', () => ({
  useTradeChartBars: vi.fn(),
}));

import { useTradeChartBars } from '../hooks/useSymbolBars';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('TradeChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with valid bars data', () => {
    vi.mocked(useTradeChartBars).mockReturnValue({
      data: mockBarsData,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useTradeChartBars>);

    render(
      <TradeChart
        symbol="TSLA"
        entryTime="2026-02-25T14:35:00Z"
        exitTime="2026-02-25T15:00:00Z"
        entryPrice={250.0}
        exitPrice={255.0}
        stopPrice={248.0}
        targetPrices={[254.0, 258.0]}
        isOpen={false}
      />,
      { wrapper: createWrapper() }
    );

    // Chart container should be visible (not invisible)
    const container = screen.getByTestId('trade-chart-container');
    expect(container).toBeInTheDocument();
    expect(container.className).not.toContain('invisible');
  });

  it('shows empty state when no bars returned', () => {
    vi.mocked(useTradeChartBars).mockReturnValue({
      data: { symbol: 'TSLA', timeframe: '1m', bars: [], count: 0 },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useTradeChartBars>);

    render(
      <TradeChart
        symbol="TSLA"
        entryTime="2026-02-25T14:35:00Z"
        entryPrice={250.0}
        isOpen={true}
      />,
      { wrapper: createWrapper() }
    );

    // Should show empty state message
    expect(screen.getByText('Bar data not available for this trade')).toBeInTheDocument();
  });

  it('creates price lines for entry, stop, T1, and T2', () => {
    vi.mocked(useTradeChartBars).mockReturnValue({
      data: mockBarsData,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useTradeChartBars>);

    render(
      <TradeChart
        symbol="TSLA"
        entryTime="2026-02-25T14:35:00Z"
        exitTime="2026-02-25T15:00:00Z"
        entryPrice={250.0}
        exitPrice={255.0}
        stopPrice={248.0}
        targetPrices={[254.0, 258.0]}
        isOpen={false}
      />,
      { wrapper: createWrapper() }
    );

    // Should create price lines for entry, stop, T1, T2, and exit (5 total)
    // Entry: blue dashed
    // Stop: red solid
    // T1: green dashed
    // T2: green dotted (since > 0)
    // Exit: orange solid (since it differs from entry by > $0.01)
    expect(mockCreatePriceLine).toHaveBeenCalledTimes(5);

    // Verify entry price line
    expect(mockCreatePriceLine).toHaveBeenCalledWith(
      expect.objectContaining({
        price: 250.0,
        title: 'Entry',
      })
    );

    // Verify stop price line
    expect(mockCreatePriceLine).toHaveBeenCalledWith(
      expect.objectContaining({
        price: 248.0,
        title: 'Stop',
      })
    );

    // Verify T1 price line
    expect(mockCreatePriceLine).toHaveBeenCalledWith(
      expect.objectContaining({
        price: 254.0,
        title: 'T1',
      })
    );

    // Verify T2 price line
    expect(mockCreatePriceLine).toHaveBeenCalledWith(
      expect.objectContaining({
        price: 258.0,
        title: 'T2',
      })
    );
  });

  it('shows loading state while fetching data', () => {
    vi.mocked(useTradeChartBars).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useTradeChartBars>);

    render(
      <TradeChart
        symbol="TSLA"
        entryTime="2026-02-25T14:35:00Z"
        entryPrice={250.0}
        isOpen={true}
      />,
      { wrapper: createWrapper() }
    );

    // Chart container should be invisible during loading
    const container = screen.getByTestId('trade-chart-container');
    expect(container.className).toContain('invisible');
  });

  it('shows error state when fetch fails', () => {
    vi.mocked(useTradeChartBars).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
    } as unknown as ReturnType<typeof useTradeChartBars>);

    render(
      <TradeChart
        symbol="TSLA"
        entryTime="2026-02-25T14:35:00Z"
        entryPrice={250.0}
        isOpen={true}
      />,
      { wrapper: createWrapper() }
    );

    // Should show error message
    expect(screen.getByText('Chart unavailable')).toBeInTheDocument();
  });

  it('shows current price line for open positions', () => {
    vi.mocked(useTradeChartBars).mockReturnValue({
      data: mockBarsData,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useTradeChartBars>);

    render(
      <TradeChart
        symbol="TSLA"
        entryTime="2026-02-25T14:35:00Z"
        entryPrice={250.0}
        currentPrice={253.5}
        stopPrice={248.0}
        targetPrices={[254.0, 258.0]}
        isOpen={true}
      />,
      { wrapper: createWrapper() }
    );

    // Should create price lines for entry, stop, T1, T2, and current (5 total, no exit)
    expect(mockCreatePriceLine).toHaveBeenCalledTimes(5);

    // Verify current price line is created
    expect(mockCreatePriceLine).toHaveBeenCalledWith(
      expect.objectContaining({
        price: 253.5,
        title: 'Current',
      })
    );
  });
});
