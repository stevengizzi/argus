/**
 * Tests for MiniChart component.
 *
 * Sprint 32.75, Session 9.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, act } from '@testing-library/react';
import { createRef } from 'react';
import * as LWC from 'lightweight-charts';
import type { UTCTimestamp } from 'lightweight-charts';
import { MiniChart } from './MiniChart';
import type { MiniChartHandle, CandleData } from './MiniChart';

// --- Lightweight Charts mock ---

const mockCreatePriceLine = vi.fn(() => ({
  applyOptions: vi.fn(),
}));
const mockRemovePriceLine = vi.fn();
const mockUpdate = vi.fn();
const mockSetData = vi.fn();
const mockFitContent = vi.fn();
const mockRemoveChart = vi.fn();
const mockApplyOptions = vi.fn();

const mockAddSeries = vi.fn(() => ({
  setData: mockSetData,
  createPriceLine: mockCreatePriceLine,
  removePriceLine: mockRemovePriceLine,
  update: mockUpdate,
}));
const mockTimeScale = vi.fn(() => ({
  fitContent: mockFitContent,
  setVisibleRange: vi.fn(),
}));

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addSeries: mockAddSeries,
    timeScale: mockTimeScale,
    remove: mockRemoveChart,
    applyOptions: mockApplyOptions,
  })),
  CandlestickSeries: 'CandlestickSeries',
  LineStyle: { Solid: 0, Dotted: 1, Dashed: 2, LargeDashed: 3 },
  // Use an inline factory so no module-level variable is referenced directly
  // in the outer factory object (which would cause a TDZ error after hoisting).
  createSeriesMarkers: vi.fn(() => ({ setMarkers: vi.fn(), markers: vi.fn(() => []) })),
}));

// --- Fixtures ---

const SAMPLE_CANDLES: CandleData[] = [
  { time: 1700000000 as CandleData['time'], open: 150, high: 152, low: 149, close: 151 },
  { time: 1700000060 as CandleData['time'], open: 151, high: 154, low: 150, close: 153 },
  { time: 1700000120 as CandleData['time'], open: 153, high: 155, low: 152, close: 154 },
];

describe('MiniChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates a chart instance on mount', () => {
    render(
      <MiniChart
        candles={SAMPLE_CANDLES}
        entryPrice={151}
        stopPrice={148}
        targetPrices={[155]}
      />,
    );

    expect(LWC.createChart).toHaveBeenCalledOnce();
    expect(mockAddSeries).toHaveBeenCalledOnce();
    expect(mockSetData).toHaveBeenCalledOnce();
  });

  it('removes the chart instance on unmount', () => {
    const { unmount } = render(
      <MiniChart candles={SAMPLE_CANDLES} />,
    );

    expect(mockRemoveChart).not.toHaveBeenCalled();
    unmount();
    expect(mockRemoveChart).toHaveBeenCalledOnce();
  });

  it('creates price lines for entry, stop, and T1', () => {
    render(
      <MiniChart
        candles={SAMPLE_CANDLES}
        entryPrice={151}
        stopPrice={148}
        targetPrices={[155]}
      />,
    );

    // Three price lines: entry + stop + T1
    expect(mockCreatePriceLine).toHaveBeenCalledTimes(3);
  });

  it('creates trailing stop price line when trailingStopPrice is provided', () => {
    render(
      <MiniChart
        candles={SAMPLE_CANDLES}
        entryPrice={151}
        stopPrice={148}
        targetPrices={[155]}
        trailingStopPrice={150}
      />,
    );

    // Four price lines: entry + stop + T1 + trailing stop
    expect(mockCreatePriceLine).toHaveBeenCalledTimes(4);
  });

  it('does not create price lines for missing/invalid price props', () => {
    render(<MiniChart candles={SAMPLE_CANDLES} />);

    // No valid price props — no price lines created
    expect(mockCreatePriceLine).not.toHaveBeenCalled();
  });

  it('fits content after candle data is set', () => {
    render(<MiniChart candles={SAMPLE_CANDLES} entryPrice={151} />);

    expect(mockTimeScale).toHaveBeenCalled();
    expect(mockFitContent).toHaveBeenCalledOnce();
  });

  it('exposes imperative handle with updateCandle, appendCandle, updateTrailingStop', () => {
    const ref = createRef<MiniChartHandle>();

    render(
      <MiniChart
        ref={ref}
        candles={SAMPLE_CANDLES}
        entryPrice={151}
        stopPrice={148}
        targetPrices={[155]}
      />,
    );

    expect(ref.current).not.toBeNull();
    expect(typeof ref.current?.updateCandle).toBe('function');
    expect(typeof ref.current?.appendCandle).toBe('function');
    expect(typeof ref.current?.updateTrailingStop).toBe('function');
  });

  it('updateCandle calls series update', () => {
    const ref = createRef<MiniChartHandle>();

    render(<MiniChart ref={ref} candles={SAMPLE_CANDLES} />);

    const newCandle: CandleData = {
      time: 1700000180 as CandleData['time'],
      open: 154,
      high: 156,
      low: 153,
      close: 155,
    };

    act(() => {
      ref.current?.updateCandle(newCandle);
    });

    expect(mockUpdate).toHaveBeenCalledWith(newCandle);
  });

  it('updateTrailingStop creates a new price line when none exists', () => {
    const ref = createRef<MiniChartHandle>();

    render(<MiniChart ref={ref} candles={SAMPLE_CANDLES} />);

    act(() => {
      ref.current?.updateTrailingStop(149.5);
    });

    expect(mockCreatePriceLine).toHaveBeenCalledWith(
      expect.objectContaining({ price: 149.5, color: '#eab308' }),
    );
  });

  it('renders the container div with correct data-testid', () => {
    const { getByTestId } = render(<MiniChart candles={SAMPLE_CANDLES} />);
    expect(getByTestId('mini-chart-container')).toBeInTheDocument();
  });

  it('creates an entry marker via createSeriesMarkers when entryTime is provided', () => {
    // entryTime matches the second candle (1700000060)
    render(
      <MiniChart
        candles={SAMPLE_CANDLES}
        entryPrice={151}
        entryTime={1700000060 as UTCTimestamp}
      />,
    );

    const createSeriesMarkersMock = vi.mocked(LWC.createSeriesMarkers);
    expect(createSeriesMarkersMock).toHaveBeenCalledOnce();
    const markers = createSeriesMarkersMock.mock.calls[0][1] as Array<{
      time: UTCTimestamp;
      shape: string;
      position: string;
    }>;
    expect(markers).toHaveLength(1);
    expect(markers[0].shape).toBe('arrowUp');
    expect(markers[0].position).toBe('belowBar');
    expect(markers[0].time).toBeLessThanOrEqual(1700000060);
  });

  it('does not call createSeriesMarkers when entryTime is not provided', () => {
    render(
      <MiniChart candles={SAMPLE_CANDLES} entryPrice={151} />,
    );

    expect(vi.mocked(LWC.createSeriesMarkers)).not.toHaveBeenCalled();
  });

  it('entry price line has axisLabelVisible false; stop and T1 have axisLabelVisible true; trail has axisLabelVisible false', () => {
    render(
      <MiniChart
        candles={SAMPLE_CANDLES}
        entryPrice={151}
        stopPrice={148}
        targetPrices={[155]}
        trailingStopPrice={150}
      />,
    );

    const calls = mockCreatePriceLine.mock.calls as Array<[{ title: string; axisLabelVisible: boolean }]>;
    const entryCall = calls.find((c) => c[0].title === 'Entry');
    const stopCall = calls.find((c) => c[0].title === 'Stop');
    const t1Call = calls.find((c) => c[0].title === 'T1');
    const trailCall = calls.find((c) => c[0].title === 'Trail');

    expect(entryCall?.[0].axisLabelVisible).toBe(false);
    expect(stopCall?.[0].axisLabelVisible).toBe(true);
    expect(t1Call?.[0].axisLabelVisible).toBe(true);
    expect(trailCall?.[0].axisLabelVisible).toBe(false);
  });
});
