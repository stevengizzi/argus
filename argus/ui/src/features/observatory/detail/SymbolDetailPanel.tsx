/**
 * Slide-out detail panel for the Observatory page.
 *
 * Shows a selected symbol's full context: pipeline position, condition grid,
 * quality score, market data, catalyst summary, strategy history, and
 * candlestick chart slot.
 *
 * Panel receives selectedSymbol: string | null. When null, panel is hidden.
 * Content swaps on symbol change without close/reopen animation.
 * Closes only on Escape or explicit close button (not canvas click).
 *
 * Sprint 25 Session 4a.
 */

import { useQuery } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { useEffect } from 'react';

import { getSymbolJourney } from '../../../api/client';
import { PIPELINE_TIERS } from '../hooks/useObservatoryKeyboard';
import { SymbolConditionGrid } from './SymbolConditionGrid';
import { SymbolStrategyHistory } from './SymbolStrategyHistory';

interface SymbolDetailPanelProps {
  selectedSymbol: string | null;
  selectedTierIndex: number;
  onClose: () => void;
}

export function SymbolDetailPanel({
  selectedSymbol,
  selectedTierIndex,
  onClose,
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
}

function SymbolDetailContent({ symbol, tierIndex, onClose }: SymbolDetailContentProps) {
  const journeyQuery = useQuery({
    queryKey: ['observatory', 'journey', symbol],
    queryFn: () => getSymbolJourney(symbol),
    enabled: symbol !== '',
    staleTime: 10_000,
    refetchInterval: 15_000,
  });

  const events = journeyQuery.data?.events ?? [];

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
          <span className="text-[10px] text-argus-text-dim">Company name pending</span>
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

      {/* Quality score placeholder */}
      <section data-testid="detail-quality-section">
        <SectionLabel>Quality</SectionLabel>
        <div className="flex items-center gap-2">
          <span className="text-xs text-argus-text-dim">Score &amp; grade — S4b</span>
        </div>
      </section>

      {/* Market data snapshot placeholder */}
      <section data-testid="detail-market-data">
        <SectionLabel>Market Data</SectionLabel>
        <div className="grid grid-cols-3 gap-2">
          <MarketDataCell label="Price" value="--" />
          <MarketDataCell label="Change" value="--" />
          <MarketDataCell label="Volume" value="--" />
          <MarketDataCell label="ATR" value="--" />
          <MarketDataCell label="VWAP" value="--" />
          <MarketDataCell label="Rel Vol" value="--" />
        </div>
      </section>

      {/* Catalyst summary placeholder */}
      <section data-testid="detail-catalyst-section">
        <SectionLabel>Catalysts</SectionLabel>
        <span className="text-xs text-argus-text-dim">No catalysts available</span>
      </section>

      {/* Strategy history */}
      <section>
        <SectionLabel>Strategy History</SectionLabel>
        <SymbolStrategyHistory events={events} />
      </section>

      {/* Candlestick chart slot */}
      <section data-testid="detail-chart-slot">
        <SectionLabel>Chart</SectionLabel>
        <div className="h-48 rounded bg-argus-surface-2/50 flex items-center justify-center">
          <span className="text-xs text-argus-text-dim">Candlestick Chart — S4b</span>
        </div>
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
