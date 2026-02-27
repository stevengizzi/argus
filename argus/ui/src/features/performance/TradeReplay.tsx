/**
 * Animated trade replay with candlestick chart and playback controls.
 *
 * Sprint 21d: The most ambitious visualization — animated candlestick
 * trade walkthrough. Shows historical bars progressively with entry/exit
 * markers, stop/target lines, and VWAP overlay.
 *
 * Features:
 * - Trade selector dropdown
 * - Candlestick chart with progressive bar reveal
 * - Playback controls: play/pause, speed (1x/2x/5x/10x), scrubber, step buttons
 * - Info panel: current time, price, unrealized P&L, R-multiple
 * - Price lines for entry, stop, T1, T2
 * - Entry/exit markers
 * - VWAP line overlay (when available)
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type CandlestickData,
  type LineData,
  type UTCTimestamp,
  type Time,
  type SeriesMarker,
  type PriceLineOptions,
} from 'lightweight-charts';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  ChevronDown,
} from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { useTradeReplay } from '../../hooks/useTradeReplay';
import { useTrades } from '../../hooks/useTrades';
import { formatCurrency, formatR } from '../../utils/format';
import { chartColors, lwcDefaultOptions } from '../../utils/chartTheme';
import { getStrategyDisplay } from '../../utils/strategyConfig';
import type { Trade, ReplayBar } from '../../api/types';

// Speed options for playback
const SPEED_OPTIONS = [1, 2, 5, 10] as const;
type PlaybackSpeed = typeof SPEED_OPTIONS[number];

interface TradeReplayProps {
  /** Optional initial trade ID to load */
  initialTradeId?: string;
}

export function TradeReplay({ initialTradeId }: TradeReplayProps) {
  // State
  const [selectedTradeId, setSelectedTradeId] = useState<string | null>(initialTradeId ?? null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [currentBarIndex, setCurrentBarIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<PlaybackSpeed>(1);

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const vwapSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const playbackIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch trades for selector (recent 50)
  const { data: tradesData } = useTrades({ limit: 50 });
  const trades = tradesData?.trades ?? [];

  // Fetch replay data for selected trade
  const { data: replayData, isLoading, error } = useTradeReplay(selectedTradeId);

  // Transform bars to chart format
  const chartData = useMemo(() => {
    if (!replayData?.bars?.length) return { candles: [], vwap: [] };

    const candles: CandlestickData<UTCTimestamp>[] = [];
    const vwap: LineData<UTCTimestamp>[] = [];

    for (let i = 0; i < replayData.bars.length; i++) {
      const bar = replayData.bars[i];
      const time = Math.floor(new Date(bar.timestamp).getTime() / 1000) as UTCTimestamp;

      candles.push({
        time,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      });

      if (replayData.vwap && replayData.vwap[i] !== undefined) {
        vwap.push({
          time,
          value: replayData.vwap[i],
        });
      }
    }

    return { candles, vwap };
  }, [replayData]);

  // Get current visible data (up to currentBarIndex)
  const visibleCandles = useMemo(() => {
    return chartData.candles.slice(0, currentBarIndex + 1);
  }, [chartData.candles, currentBarIndex]);

  const visibleVwap = useMemo(() => {
    return chartData.vwap.slice(0, currentBarIndex + 1);
  }, [chartData.vwap, currentBarIndex]);

  // Current bar data
  const currentBar = replayData?.bars[currentBarIndex];
  const entryPrice = replayData?.trade.entry_price ?? 0;
  const stopPrice = replayData?.trade.entry_price
    ? replayData.trade.entry_price * 0.99 // Approximate stop if not available
    : 0;
  const riskPerShare = entryPrice - stopPrice;

  // Calculate unrealized P&L (only after entry bar)
  const unrealizedPnl = useMemo(() => {
    if (!currentBar || !replayData || currentBarIndex < replayData.entry_bar_index) {
      return null;
    }
    const shares = replayData.trade.shares;
    const side = replayData.trade.side;
    const currentPrice = currentBar.close;

    if (side === 'buy' || side === 'long') {
      return (currentPrice - entryPrice) * shares;
    } else {
      return (entryPrice - currentPrice) * shares;
    }
  }, [currentBar, replayData, currentBarIndex, entryPrice]);

  // Calculate R-multiple
  const currentRMultiple = useMemo(() => {
    if (unrealizedPnl === null || riskPerShare === 0) return null;
    const shares = replayData?.trade.shares ?? 1;
    return unrealizedPnl / (riskPerShare * shares);
  }, [unrealizedPnl, riskPerShare, replayData?.trade.shares]);

  // Markers for entry/exit
  const markers = useMemo((): SeriesMarker<UTCTimestamp>[] => {
    if (!replayData || !chartData.candles.length) return [];

    const result: SeriesMarker<UTCTimestamp>[] = [];
    const entryIdx = replayData.entry_bar_index;
    const exitIdx = replayData.exit_bar_index;

    // Entry marker (only show if we've reached that bar)
    if (entryIdx <= currentBarIndex && chartData.candles[entryIdx]) {
      result.push({
        time: chartData.candles[entryIdx].time,
        position: 'belowBar',
        color: chartColors.profit,
        shape: 'arrowUp',
        text: 'Entry',
      });
    }

    // Exit marker (only show if we've reached that bar)
    if (exitIdx !== null && exitIdx <= currentBarIndex && chartData.candles[exitIdx]) {
      const isWin = (replayData.trade.pnl_dollars ?? 0) >= 0;
      result.push({
        time: chartData.candles[exitIdx].time,
        position: 'aboveBar',
        color: isWin ? chartColors.profit : chartColors.loss,
        shape: 'arrowDown',
        text: 'Exit',
      });
    }

    return result;
  }, [replayData, chartData.candles, currentBarIndex]);

  // Total bars
  const totalBars = chartData.candles.length;
  const hasReachedEntry = replayData ? currentBarIndex >= replayData.entry_bar_index : false;
  const hasReachedExit = replayData && replayData.exit_bar_index !== null
    ? currentBarIndex >= replayData.exit_bar_index
    : false;

  // Create/destroy chart
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      ...lwcDefaultOptions,
      width: container.clientWidth,
      height: 350,
      timeScale: {
        ...lwcDefaultOptions.timeScale,
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: chartColors.profit,
      downColor: chartColors.loss,
      borderVisible: false,
      wickUpColor: chartColors.profit,
      wickDownColor: chartColors.loss,
    });
    candleSeriesRef.current = candleSeries;

    // Create markers plugin for entry/exit markers
    const markersPlugin = createSeriesMarkers(candleSeries, []);
    markersPluginRef.current = markersPlugin;

    // Add VWAP line series
    const vwapSeries = chart.addSeries(LineSeries, {
      color: chartColors.primary,
      lineWidth: 1,
      lineStyle: 0, // Solid
      priceLineVisible: false,
      lastValueVisible: false,
    });
    vwapSeriesRef.current = vwapSeries;

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
      if (chartRef.current && container) {
        chartRef.current.applyOptions({
          width: container.clientWidth,
        });
      }
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      vwapSeriesRef.current = null;
      markersPluginRef.current = null;
    };
  }, []);

  // Update chart data when visible range changes
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const vwapSeries = vwapSeriesRef.current;
    const chart = chartRef.current;

    if (!candleSeries || !chart) return;

    // Set visible data
    candleSeries.setData(visibleCandles);
    if (vwapSeries && visibleVwap.length > 0) {
      vwapSeries.setData(visibleVwap);
    }

    // Set markers via plugin
    if (markersPluginRef.current) {
      markersPluginRef.current.setMarkers(markers);
    }

    // Fit content
    if (visibleCandles.length > 0) {
      chart.timeScale().fitContent();
    }
  }, [visibleCandles, visibleVwap, markers]);

  // Add price lines when trade data loads
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    if (!candleSeries || !replayData?.trade) return;

    // Clear existing price lines
    const existingLines = candleSeries.priceLines?.() ?? [];
    existingLines.forEach((line) => candleSeries.removePriceLine(line));

    const trade = replayData.trade;
    const lines: PriceLineOptions[] = [];

    // Common price line options
    const basePriceLineOptions = {
      lineWidth: 1 as const,
      lineStyle: 2 as const, // Dashed
      lineVisible: true,
      axisLabelVisible: true,
      axisLabelColor: chartColors.surface,
      axisLabelTextColor: chartColors.text,
    };

    // Entry line
    if (trade.entry_price) {
      lines.push({
        ...basePriceLineOptions,
        price: trade.entry_price,
        color: chartColors.profit,
        title: 'Entry',
      });
    }

    // Stop line (approximate)
    const stopPriceEst = trade.entry_price * 0.99;
    lines.push({
      ...basePriceLineOptions,
      price: stopPriceEst,
      color: chartColors.loss,
      title: 'Stop',
    });

    // T1 line (1R target)
    const t1Price = trade.entry_price + (trade.entry_price - stopPriceEst);
    lines.push({
      ...basePriceLineOptions,
      price: t1Price,
      color: chartColors.primary,
      title: 'T1',
    });

    // T2 line (2R target)
    const t2Price = trade.entry_price + 2 * (trade.entry_price - stopPriceEst);
    lines.push({
      ...basePriceLineOptions,
      price: t2Price,
      color: chartColors.primary,
      title: 'T2',
    });

    // Add lines
    lines.forEach((lineOptions) => {
      candleSeries.createPriceLine(lineOptions);
    });
  }, [replayData?.trade]);

  // Reset playback when trade changes
  useEffect(() => {
    setCurrentBarIndex(0);
    setIsPlaying(false);
  }, [selectedTradeId]);

  // Playback interval
  useEffect(() => {
    if (isPlaying && totalBars > 0) {
      const intervalMs = 1000 / speed;
      playbackIntervalRef.current = setInterval(() => {
        setCurrentBarIndex((prev) => {
          if (prev >= totalBars - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, intervalMs);
    }

    return () => {
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current);
        playbackIntervalRef.current = null;
      }
    };
  }, [isPlaying, speed, totalBars]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handlers
  const handlePlayPause = useCallback(() => {
    if (currentBarIndex >= totalBars - 1) {
      // Reset to start if at end
      setCurrentBarIndex(0);
    }
    setIsPlaying((prev) => !prev);
  }, [currentBarIndex, totalBars]);

  const handleStepBack = useCallback(() => {
    setIsPlaying(false);
    setCurrentBarIndex((prev) => Math.max(0, prev - 1));
  }, []);

  const handleStepForward = useCallback(() => {
    setIsPlaying(false);
    setCurrentBarIndex((prev) => Math.min(totalBars - 1, prev + 1));
  }, [totalBars]);

  const handleReset = useCallback(() => {
    setIsPlaying(false);
    setCurrentBarIndex(0);
  }, []);

  const handleScrub = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setIsPlaying(false);
    setCurrentBarIndex(parseInt(e.target.value, 10));
  }, []);

  const handleSpeedChange = useCallback((newSpeed: PlaybackSpeed) => {
    setSpeed(newSpeed);
  }, []);

  const handleTradeSelect = useCallback((tradeId: string) => {
    setSelectedTradeId(tradeId);
    setIsDropdownOpen(false);
  }, []);

  // Format trade option label
  const formatTradeOption = (trade: Trade): string => {
    const date = new Date(trade.entry_time).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
    const pnl = trade.pnl_dollars
      ? `${trade.pnl_dollars >= 0 ? '+' : ''}${formatCurrency(trade.pnl_dollars)}`
      : '';
    return `${trade.symbol} ${trade.side} ${date} ${pnl}`;
  };

  // Get selected trade
  const selectedTrade = trades.find((t) => t.id === selectedTradeId);

  // No trade selected
  if (!selectedTradeId) {
    return (
      <Card>
        <CardHeader title="Trade Replay" />
        <div className="px-4 pb-4">
          <TradeSelector
            ref={dropdownRef}
            trades={trades}
            selectedTrade={null}
            isOpen={isDropdownOpen}
            onToggle={() => setIsDropdownOpen(!isDropdownOpen)}
            onSelect={handleTradeSelect}
            formatOption={formatTradeOption}
          />
          <div className="mt-8 text-center text-argus-text-dim py-12">
            Select a trade to replay
          </div>
        </div>
      </Card>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Trade Replay" />
        <div className="px-4 pb-4">
          <TradeSelector
            ref={dropdownRef}
            trades={trades}
            selectedTrade={selectedTrade ?? null}
            isOpen={isDropdownOpen}
            onToggle={() => setIsDropdownOpen(!isDropdownOpen)}
            onSelect={handleTradeSelect}
            formatOption={formatTradeOption}
          />
          <div className="h-[350px] animate-pulse bg-argus-surface-3 rounded-lg mt-4" />
        </div>
      </Card>
    );
  }

  // Error or no data
  if (error || !replayData || replayData.bars.length === 0) {
    return (
      <Card>
        <CardHeader title="Trade Replay" />
        <div className="px-4 pb-4">
          <TradeSelector
            ref={dropdownRef}
            trades={trades}
            selectedTrade={selectedTrade ?? null}
            isOpen={isDropdownOpen}
            onToggle={() => setIsDropdownOpen(!isDropdownOpen)}
            onSelect={handleTradeSelect}
            formatOption={formatTradeOption}
          />
          <div className="mt-8 text-center text-argus-text-dim py-12">
            Bar data not available for this trade
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card noPadding>
      <div className="p-4 pb-0">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <CardHeader title="Trade Replay" />
          <div className="w-full lg:w-72">
            <TradeSelector
              ref={dropdownRef}
              trades={trades}
              selectedTrade={selectedTrade ?? null}
              isOpen={isDropdownOpen}
              onToggle={() => setIsDropdownOpen(!isDropdownOpen)}
              onSelect={handleTradeSelect}
              formatOption={formatTradeOption}
            />
          </div>
        </div>
      </div>

      {/* Chart + Info Panel layout */}
      <div className="p-4 pt-2">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Chart area - 70% on desktop */}
          <div className="flex-1 lg:flex-[7]">
            <div
              ref={containerRef}
              className="bg-argus-surface-2 rounded-lg border border-argus-border overflow-hidden"
              style={{ height: 350 }}
            />

            {/* Playback controls */}
            <div className="mt-4 space-y-3">
              {/* Scrubber */}
              <input
                type="range"
                min={0}
                max={Math.max(0, totalBars - 1)}
                value={currentBarIndex}
                onChange={handleScrub}
                className="w-full h-2 bg-argus-surface-3 rounded-lg appearance-none cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                  [&::-webkit-slider-thumb]:bg-argus-accent [&::-webkit-slider-thumb]:rounded-full
                  [&::-webkit-slider-thumb]:cursor-pointer"
                disabled={totalBars === 0}
              />

              {/* Control buttons */}
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  {/* Reset */}
                  <button
                    onClick={handleReset}
                    className="p-2 rounded-lg bg-argus-surface-2 hover:bg-argus-surface-3
                      text-argus-text-dim hover:text-argus-text transition-colors"
                    title="Reset"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </button>

                  {/* Step back */}
                  <button
                    onClick={handleStepBack}
                    disabled={currentBarIndex === 0}
                    className="p-2 rounded-lg bg-argus-surface-2 hover:bg-argus-surface-3
                      text-argus-text-dim hover:text-argus-text transition-colors
                      disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Step back"
                  >
                    <SkipBack className="w-4 h-4" />
                  </button>

                  {/* Play/Pause */}
                  <button
                    onClick={handlePlayPause}
                    className="p-3 rounded-lg bg-argus-accent hover:bg-argus-accent/90
                      text-white transition-colors"
                    title={isPlaying ? 'Pause' : 'Play'}
                  >
                    {isPlaying ? (
                      <Pause className="w-5 h-5" />
                    ) : (
                      <Play className="w-5 h-5" />
                    )}
                  </button>

                  {/* Step forward */}
                  <button
                    onClick={handleStepForward}
                    disabled={currentBarIndex >= totalBars - 1}
                    className="p-2 rounded-lg bg-argus-surface-2 hover:bg-argus-surface-3
                      text-argus-text-dim hover:text-argus-text transition-colors
                      disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Step forward"
                  >
                    <SkipForward className="w-4 h-4" />
                  </button>
                </div>

                {/* Speed selector */}
                <div className="flex items-center gap-1">
                  {SPEED_OPTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSpeedChange(s)}
                      className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors
                        ${speed === s
                          ? 'bg-argus-accent text-white'
                          : 'bg-argus-surface-2 text-argus-text-dim hover:bg-argus-surface-3 hover:text-argus-text'
                        }`}
                    >
                      {s}x
                    </button>
                  ))}
                </div>

                {/* Bar counter */}
                <span className="text-xs text-argus-text-dim tabular-nums">
                  {currentBarIndex + 1} / {totalBars}
                </span>
              </div>
            </div>
          </div>

          {/* Info panel - 30% on desktop */}
          <div className="lg:flex-[3] space-y-4">
            <InfoPanel
              currentBar={currentBar}
              trade={replayData.trade}
              unrealizedPnl={unrealizedPnl}
              rMultiple={currentRMultiple}
              hasReachedEntry={hasReachedEntry}
              hasReachedExit={hasReachedExit}
            />
          </div>
        </div>
      </div>
    </Card>
  );
}

// Trade selector dropdown
interface TradeSelectorProps {
  trades: Trade[];
  selectedTrade: Trade | null;
  isOpen: boolean;
  onToggle: () => void;
  onSelect: (tradeId: string) => void;
  formatOption: (trade: Trade) => string;
}

const TradeSelector = ({
  trades,
  selectedTrade,
  isOpen,
  onToggle,
  onSelect,
  formatOption,
}: TradeSelectorProps & { ref?: React.Ref<HTMLDivElement> }) => {
  const dropdownRef = useRef<HTMLDivElement>(null);

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-2 px-3 py-2
          bg-argus-surface-2 border border-argus-border rounded-lg
          text-sm text-argus-text hover:bg-argus-surface-3 transition-colors"
      >
        <span className="truncate">
          {selectedTrade ? formatOption(selectedTrade) : 'Select a trade...'}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-argus-text-dim transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isOpen && (
        <div
          className="absolute z-50 mt-1 w-full max-h-60 overflow-auto
            bg-argus-surface-2 border border-argus-border rounded-lg shadow-lg"
        >
          {trades.length === 0 ? (
            <div className="px-3 py-2 text-sm text-argus-text-dim">
              No trades available
            </div>
          ) : (
            trades.map((trade) => (
              <button
                key={trade.id}
                onClick={() => onSelect(trade.id)}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-argus-surface-3
                  ${trade.id === selectedTrade?.id ? 'bg-argus-surface-3 text-argus-accent' : 'text-argus-text'}`}
              >
                {formatOption(trade)}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
};

// Info panel component
interface InfoPanelProps {
  currentBar: ReplayBar | undefined;
  trade: Trade;
  unrealizedPnl: number | null;
  rMultiple: number | null;
  hasReachedEntry: boolean;
  hasReachedExit: boolean;
}

function InfoPanel({
  currentBar,
  trade,
  unrealizedPnl,
  rMultiple,
  hasReachedEntry,
  hasReachedExit,
}: InfoPanelProps) {
  // Format current time
  const currentTime = currentBar
    ? new Date(currentBar.timestamp).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      })
    : '--:--';

  // Trade outcome
  const pnl = trade.pnl_dollars ?? 0;
  const rMult = trade.pnl_r_multiple ?? 0;
  const isWin = pnl >= 0;

  return (
    <div className="bg-argus-surface-2 rounded-lg border border-argus-border p-4 space-y-4">
      {/* Trade info */}
      <div>
        <div className="text-xs text-argus-text-dim uppercase tracking-wider mb-2">
          Trade Info
        </div>
        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span className="text-argus-text-dim">Symbol</span>
            <span className="text-argus-text font-medium">{trade.symbol}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-argus-text-dim">Side</span>
            <span className="text-argus-text capitalize">{trade.side}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-argus-text-dim">Strategy</span>
            <span className="text-argus-text">
              {getStrategyDisplay(trade.strategy_id.replace('strat_', '')).name}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-argus-text-dim">Shares</span>
            <span className="text-argus-text">{trade.shares}</span>
          </div>
        </div>
      </div>

      {/* Current state */}
      <div>
        <div className="text-xs text-argus-text-dim uppercase tracking-wider mb-2">
          Current Position
        </div>
        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span className="text-argus-text-dim">Time</span>
            <span className="text-argus-text tabular-nums">{currentTime}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-argus-text-dim">Price</span>
            <span className="text-argus-text tabular-nums">
              {currentBar ? formatCurrency(currentBar.close) : '--'}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-argus-text-dim">Unrealized P&L</span>
            <span
              className={`tabular-nums font-medium ${
                !hasReachedEntry
                  ? 'text-argus-text-dim'
                  : unrealizedPnl === null
                  ? 'text-argus-text-dim'
                  : unrealizedPnl >= 0
                  ? 'text-argus-profit'
                  : 'text-argus-loss'
              }`}
            >
              {!hasReachedEntry
                ? 'Not in trade'
                : unrealizedPnl !== null
                ? `${unrealizedPnl >= 0 ? '+' : ''}${formatCurrency(unrealizedPnl)}`
                : '--'}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-argus-text-dim">R-Multiple</span>
            <span
              className={`tabular-nums font-medium ${
                !hasReachedEntry
                  ? 'text-argus-text-dim'
                  : rMultiple === null
                  ? 'text-argus-text-dim'
                  : rMultiple >= 0
                  ? 'text-argus-profit'
                  : 'text-argus-loss'
              }`}
            >
              {!hasReachedEntry
                ? '--'
                : rMultiple !== null
                ? formatR(rMultiple).text
                : '--'}
            </span>
          </div>
        </div>
      </div>

      {/* Trade result (after exit) */}
      {hasReachedExit && (
        <div>
          <div className="text-xs text-argus-text-dim uppercase tracking-wider mb-2">
            Trade Result
          </div>
          <div className="flex items-center gap-3">
            <div
              className={`text-2xl font-bold tabular-nums ${
                isWin ? 'text-argus-profit' : 'text-argus-loss'
              }`}
            >
              {pnl >= 0 ? '+' : ''}
              {formatCurrency(pnl)}
            </div>
            <div
              className={`px-2 py-0.5 rounded text-xs font-medium ${
                isWin
                  ? 'bg-argus-profit/20 text-argus-profit'
                  : 'bg-argus-loss/20 text-argus-loss'
              }`}
            >
              {formatR(rMult).text}
            </div>
          </div>
        </div>
      )}

      {/* Status indicator */}
      {!hasReachedExit && (
        <div className="pt-2 border-t border-argus-border">
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                hasReachedEntry ? 'bg-argus-profit animate-pulse' : 'bg-argus-text-dim'
              }`}
            />
            <span className="text-xs text-argus-text-dim">
              {hasReachedEntry ? 'In trade' : 'Waiting for entry'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
