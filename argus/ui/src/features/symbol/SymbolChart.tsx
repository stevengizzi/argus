/**
 * Symbol candlestick chart placeholder.
 *
 * Session 7: Placeholder component showing symbol header and chart stub.
 * Session 8: Full LWChart candlestick implementation.
 */

import { LineChart } from 'lucide-react';
import { usePositions } from '../../hooks/usePositions';
import { formatPrice } from '../../utils/format';

interface SymbolChartProps {
  symbol: string;
}

export function SymbolChart({ symbol }: SymbolChartProps) {
  const { data: positionsData } = usePositions();

  // Try to get current price from positions data
  const position = positionsData?.positions.find((p) => p.symbol === symbol);
  const currentPrice = position?.current_price;

  return (
    <div className="space-y-3">
      {/* Header with symbol and price */}
      <div className="flex items-baseline justify-between">
        <h2 className="text-2xl font-bold text-argus-text">{symbol}</h2>
        {currentPrice != null ? (
          <span className="text-xl font-medium tabular-nums text-argus-text">
            {formatPrice(currentPrice)}
          </span>
        ) : (
          <span className="text-sm text-argus-text-dim">Price data loading...</span>
        )}
      </div>

      {/* Chart placeholder */}
      <div className="bg-argus-surface-2 rounded-lg h-64 flex flex-col items-center justify-center gap-3 border border-argus-border">
        <LineChart className="w-12 h-12 text-argus-text-dim" />
        <span className="text-sm text-argus-text-dim">
          Candlestick chart loading in Session 8
        </span>
      </div>
    </div>
  );
}
