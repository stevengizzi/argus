/**
 * Symbol detail slide-in panel.
 *
 * Global panel for inspecting any symbol. Triggered via useSymbolDetailUI store.
 * Available across all pages through AppShell mounting.
 *
 * Sections:
 * - SymbolChart: price header + candlestick chart (placeholder in Session 7)
 * - SymbolTradingHistory: your trading history on this symbol
 * - SymbolPositionDetail: current open position (if any)
 */

import { SlideInPanel } from '../../components/SlideInPanel';
import { useSymbolDetailUI } from '../../stores/symbolDetailUI';
import { SymbolChart } from './SymbolChart';
import { SymbolTradingHistory } from './SymbolTradingHistory';
import { SymbolPositionDetail } from './SymbolPositionDetail';

export function SymbolDetailPanel() {
  const { selectedSymbol, isOpen, close } = useSymbolDetailUI();

  if (!selectedSymbol) {
    return null;
  }

  return (
    <SlideInPanel
      isOpen={isOpen}
      onClose={close}
      title={selectedSymbol}
    >
      <div className="space-y-6">
        <SymbolChart symbol={selectedSymbol} />
        <SymbolPositionDetail symbol={selectedSymbol} />
        <SymbolTradingHistory symbol={selectedSymbol} />
      </div>
    </SlideInPanel>
  );
}
