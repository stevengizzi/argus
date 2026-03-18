/**
 * Slide-out detail panel for the Observatory page.
 *
 * Shows a selected symbol's full context: pipeline position, condition grid,
 * quality score, market data, catalyst summary, strategy history, and
 * candlestick chart.
 *
 * Panel receives selectedSymbol: string | null. When null, panel is hidden.
 * Content swaps on symbol change without close/reopen animation.
 * Closes only on Escape or explicit close button (not canvas click).
 *
 * Sprint 25 Sessions 4a + 4b.
 */

import { AnimatePresence, motion } from 'framer-motion';
import { useEffect } from 'react';

import { PIPELINE_TIERS } from '../hooks/useObservatoryKeyboard';
import { useSymbolDetail } from '../hooks/useSymbolDetail';
import { SymbolCandlestickChart } from './SymbolCandlestickChart';
import { SymbolConditionGrid } from './SymbolConditionGrid';
import { SymbolStrategyHistory } from './SymbolStrategyHistory';

interface SymbolDetailPanelProps {
  selectedSymbol: string | null;
  selectedTierIndex: number;
  onClose: () => void;
  date?: string;
}

export function SymbolDetailPanel({
  selectedSymbol,
  selectedTierIndex,
  onClose,
  date,
}: SymbolDetailPanelProps) {
  const isOpen = selectedSymbol !== null;

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="symbol-detail-panel"
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 320, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="shrink-0 border-l border-argus-border bg-argus-surface overflow-hidden"
          data-testid="symbol-detail-panel"
        >
          <div className="w-[320px] h-full overflow-y-auto">
            <SymbolDetailContent
              symbol={selectedSymbol}
              tierIndex={selectedTierIndex}
              onClose={onClose}
              date={date}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

interface SymbolDetailContentProps {
  symbol: string;
  tierIndex: number;
  onClose: () => void;
  date?: string;
}

const GRADE_COLORS: Record<string, string> = {
  A: 'text-green-400 bg-green-400/10',
  B: 'text-blue-400 bg-blue-400/10',
  C: 'text-yellow-400 bg-yellow-400/10',
  D: 'text-orange-400 bg-orange-400/10',
  F: 'text-red-400 bg-red-400/10',
};

function formatVolume(vol: number): string {
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`;
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(0)}K`;
  return String(vol);
}

function SymbolDetailContent({ symbol, tierIndex, onClose, date }: SymbolDetailContentProps) {
  const { journey, quality, catalysts, candles } = useSymbolDetail({ symbol, date });

  const events = journey?.events ?? [];
  const bars = candles?.bars ?? [];
  const lastBar = bars.length > 0 ? bars[bars.length - 1] : null;
  const firstBar = bars.length > 0 ? bars[0] : null;

  const priceChange = lastBar && firstBar
    ? ((lastBar.close - firstBar.open) / firstBar.open) * 100
    : null;

  const totalVolume = bars.reduce((sum, bar) => sum + bar.volume, 0);

  return (
    <div className="p-4 space-y-4">
      {/* Header: symbol + close button */}
      <div className="flex items-center justify-between">
        <div>
          <h3
            className="text-lg font-bold text-argus-text tracking-tight"
            data-testid="detail-symbol-name"
          >
            {symbol}
          </h3>
          {lastBar && (
            <span className="text-[10px] font-mono text-argus-text-dim">
              ${lastBar.close.toFixed(2)}
              {priceChange !== null && (
                <span className={priceChange >= 0 ? 'text-green-400 ml-1' : 'text-red-400 ml-1'}>
                  {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
                </span>
              )}
            </span>
          )}
          {!lastBar && (
            <span className="text-[10px] text-argus-text-dim">Loading...</span>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-argus-text-dim hover:text-argus-text text-sm px-1.5 py-0.5 rounded hover:bg-argus-surface-2 transition-colors"
          data-testid="detail-close-button"
          aria-label="Close detail panel"
        >
          &times;
        </button>
      </div>

      {/* Pipeline position badge */}
      <div data-testid="detail-pipeline-badge">
        <span className="text-[10px] font-medium text-argus-accent bg-argus-accent/10 px-2 py-0.5 rounded">
          {PIPELINE_TIERS[tierIndex]}
        </span>
      </div>

      {/* Condition grid */}
      <section>
        <SectionLabel>Conditions</SectionLabel>
        <SymbolConditionGrid events={events} />
      </section>

      {/* Quality score */}
      <section data-testid="detail-quality-section">
        <SectionLabel>Quality</SectionLabel>
        {quality ? (
          <div className="flex items-center gap-2">
            <span
              className={`text-xs font-bold px-1.5 py-0.5 rounded ${GRADE_COLORS[quality.grade] ?? 'text-argus-text-dim bg-argus-surface-2'}`}
              data-testid="detail-quality-grade"
            >
              {quality.grade}
            </span>
            <span className="text-xs font-mono text-argus-text" data-testid="detail-quality-score">
              {quality.score.toFixed(1)}
            </span>
          </div>
        ) : (
          <span className="text-xs text-argus-text-dim">No quality data</span>
        )}
      </section>

      {/* Market data snapshot */}
      <section data-testid="detail-market-data">
        <SectionLabel>Market Data</SectionLabel>
        <div className="grid grid-cols-3 gap-2">
          <MarketDataCell
            label="Price"
            value={lastBar ? `$${lastBar.close.toFixed(2)}` : '--'}
          />
          <MarketDataCell
            label="Change"
            value={priceChange !== null ? `${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)}%` : '--'}
          />
          <MarketDataCell
            label="Volume"
            value={totalVolume > 0 ? formatVolume(totalVolume) : '--'}
          />
          <MarketDataCell
            label="High"
            value={lastBar ? `$${lastBar.high.toFixed(2)}` : '--'}
          />
          <MarketDataCell
            label="Low"
            value={lastBar ? `$${lastBar.low.toFixed(2)}` : '--'}
          />
          <MarketDataCell
            label="Open"
            value={firstBar ? `$${firstBar.open.toFixed(2)}` : '--'}
          />
        </div>
      </section>

      {/* Catalyst summary */}
      <section data-testid="detail-catalyst-section">
        <SectionLabel>Catalysts</SectionLabel>
        {catalysts && catalysts.catalysts.length > 0 ? (
          <div className="space-y-1.5">
            {catalysts.catalysts.map((cat, i) => (
              <div key={i} className="text-xs">
                <span className="text-argus-text-dim">{cat.category}</span>
                <p className="text-argus-text leading-tight truncate" title={cat.headline}>
                  {cat.headline}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <span className="text-xs text-argus-text-dim">No catalysts available</span>
        )}
      </section>

      {/* Strategy history */}
      <section>
        <SectionLabel>Strategy History</SectionLabel>
        <SymbolStrategyHistory events={events} />
      </section>

      {/* Candlestick chart */}
      <section data-testid="detail-chart-slot">
        <SectionLabel>Chart</SectionLabel>
        {bars.length > 0 ? (
          <SymbolCandlestickChart symbol={symbol} bars={bars} height={200} />
        ) : (
          <div className="h-48 rounded bg-argus-surface-2/50 flex items-center justify-center">
            <span className="text-xs text-argus-text-dim">No chart data available</span>
          </div>
        )}
      </section>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="text-[10px] font-semibold text-argus-text-dim uppercase tracking-wider mb-1.5">
      {children}
    </h4>
  );
}

function MarketDataCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <div className="text-[10px] text-argus-text-dim">{label}</div>
      <div className="text-xs font-mono text-argus-text">{value}</div>
    </div>
  );
}
