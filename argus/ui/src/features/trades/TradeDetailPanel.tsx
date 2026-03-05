/**
 * Trade detail slide-in panel.
 *
 * Shows comprehensive trade details including entry/exit, P&L, levels, and exit reason explanation.
 * Uses the shared SlideInPanel component for consistent slide-in behavior.
 */

import { TrendingUp, TrendingDown, Target, Shield, Clock, ExternalLink } from 'lucide-react';
import { SlideInPanel } from '../../components/SlideInPanel';
import { Badge } from '../../components/Badge';
import { useSymbolDetailUI } from '../../stores/symbolDetailUI';
import type { Trade } from '../../api/types';
import {
  formatCurrency,
  formatPrice,
  formatDuration,
  formatDateTime,
  formatPnl,
  formatPnlPercent,
  formatR,
  formatDate,
} from '../../utils/format';

interface TradeDetailPanelProps {
  trade: Trade | null;
  onClose: () => void;
}

/**
 * Exit reason human-readable explanations.
 */
const EXIT_REASON_EXPLANATIONS: Record<string, string> = {
  target_1: 'Target 1 hit — partial profit taken',
  t1: 'Target 1 hit — partial profit taken',
  target_2: 'Target 2 hit — full profit target reached',
  t2: 'Target 2 hit — full profit target reached',
  stop_loss: 'Stop loss triggered — risk limit reached',
  sl: 'Stop loss triggered — risk limit reached',
  stop: 'Stop loss triggered — risk limit reached',
  time_stop: 'Time stop expired — maximum hold duration exceeded',
  time: 'Time stop expired — maximum hold duration exceeded',
  timeout: 'Time stop expired — maximum hold duration exceeded',
  eod: 'End of day flatten — position closed before market close',
  end_of_day: 'End of day flatten — position closed before market close',
  manual: 'Manual close — position closed by operator',
  circuit_breaker: 'Circuit breaker — emergency risk stop triggered',
};

/**
 * Get exit reason badge variant.
 */
function getExitReasonVariant(
  exitReason: string | null
): 'success' | 'danger' | 'warning' | 'neutral' {
  if (!exitReason) return 'neutral';

  const reason = exitReason.toLowerCase();
  if (reason === 'target_1' || reason === 't1' || reason === 'target_2' || reason === 't2') {
    return 'success';
  }
  if (reason === 'stop_loss' || reason === 'sl' || reason === 'stop' || reason === 'circuit_breaker') {
    return 'danger';
  }
  if (reason === 'time_stop' || reason === 'time' || reason === 'timeout') {
    return 'warning';
  }
  return 'neutral';
}

/**
 * Format exit reason for badge display.
 */
function formatExitReasonBadge(exitReason: string | null): string {
  if (!exitReason) return 'UNKNOWN';

  const reason = exitReason.toLowerCase();
  if (reason === 'target_1') return 'T1';
  if (reason === 'target_2') return 'T2';
  if (reason === 'stop_loss') return 'SL';
  if (reason === 'time_stop' || reason === 'timeout') return 'TIME';
  if (reason === 'end_of_day') return 'EOD';
  if (reason === 'manual') return 'MANUAL';
  if (reason === 'circuit_breaker') return 'CB';
  return exitReason.toUpperCase().slice(0, 6);
}

/**
 * Get exit reason explanation text.
 */
function getExitExplanation(exitReason: string | null): string {
  if (!exitReason) return 'Exit reason not recorded';
  const reason = exitReason.toLowerCase();
  return EXIT_REASON_EXPLANATIONS[reason] || `Exit: ${exitReason}`;
}

export function TradeDetailPanel({ trade, onClose }: TradeDetailPanelProps) {
  const isOpen = trade !== null;
  const { open: openSymbolDetail } = useSymbolDetailUI();

  const handleSymbolClick = () => {
    if (trade) {
      openSymbolDetail(trade.symbol);
      onClose(); // Close trade panel when opening symbol panel
    }
  };

  // Calculate P&L percentage if we have the data
  const pnlPercent =
    trade?.pnl_dollars != null && trade?.entry_price
      ? (trade.pnl_dollars / (trade.entry_price * trade.shares)) * 100
      : null;

  return (
    <SlideInPanel
      isOpen={isOpen}
      onClose={onClose}
      title={trade ? `${trade.symbol} — ${trade.side.toUpperCase()}` : ''}
      subtitle={trade?.entry_time ? formatDate(trade.entry_time) : undefined}
    >
      {trade && (
        <div className="space-y-6">
          {/* Clickable symbol link */}
          <button
            onClick={handleSymbolClick}
            className="flex items-center gap-1.5 text-lg font-semibold text-argus-accent hover:underline transition-colors"
          >
            {trade.symbol}
            <ExternalLink className="w-4 h-4" />
          </button>

          {/* Strategy badge */}
          <div className="flex items-center gap-2">
            <Badge variant="info">{trade.strategy_id}</Badge>
          </div>

          {/* P&L Summary */}
          <div className="bg-argus-surface-2 rounded-lg p-4">
            <div className="text-sm text-argus-text-dim mb-1">Profit / Loss</div>
            <div className="flex items-baseline gap-3">
              {trade.pnl_dollars != null ? (
                <>
                  <span className={`text-3xl font-bold tabular-nums ${formatPnl(trade.pnl_dollars).className}`}>
                    {formatPnl(trade.pnl_dollars).text}
                  </span>
                  {pnlPercent !== null && (
                    <span className={`text-lg tabular-nums ${formatPnlPercent(pnlPercent).className}`}>
                      {formatPnlPercent(pnlPercent).text}
                    </span>
                  )}
                </>
              ) : (
                <span className="text-3xl font-bold text-argus-text-dim">Open</span>
              )}
            </div>
            {trade.pnl_r_multiple != null && (
              <div className={`text-sm mt-1 ${formatR(trade.pnl_r_multiple).className}`}>
                {formatR(trade.pnl_r_multiple).text} R-multiple
              </div>
            )}
          </div>

          {/* Entry / Exit */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-argus-surface-2 rounded-lg p-4">
              <div className="flex items-center gap-2 text-argus-text-dim mb-2">
                <TrendingUp className="w-4 h-4" />
                <span className="text-sm">Entry</span>
              </div>
              <div className="text-lg font-medium tabular-nums">{formatPrice(trade.entry_price)}</div>
              <div className="text-sm text-argus-text-dim">{formatDateTime(trade.entry_time)}</div>
            </div>
            <div className="bg-argus-surface-2 rounded-lg p-4">
              <div className="flex items-center gap-2 text-argus-text-dim mb-2">
                <TrendingDown className="w-4 h-4" />
                <span className="text-sm">Exit</span>
              </div>
              {trade.exit_price != null && trade.exit_time ? (
                <>
                  <div className="text-lg font-medium tabular-nums">{formatPrice(trade.exit_price)}</div>
                  <div className="text-sm text-argus-text-dim">{formatDateTime(trade.exit_time)}</div>
                </>
              ) : (
                <div className="text-lg font-medium text-argus-text-dim">—</div>
              )}
            </div>
          </div>

          {/* Exit Reason */}
          {trade.exit_reason && (
            <div className="bg-argus-surface-2 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-argus-text-dim">Exit Reason</span>
                <Badge variant={getExitReasonVariant(trade.exit_reason)}>
                  {formatExitReasonBadge(trade.exit_reason)}
                </Badge>
              </div>
              <div className="text-sm text-argus-text">{getExitExplanation(trade.exit_reason)}</div>
            </div>
          )}

          {/* Trade Details */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-argus-text-dim uppercase tracking-wider">Details</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-argus-text-dim">Side</span>
                <span className={trade.side === 'long' ? 'text-argus-profit' : 'text-argus-loss'}>
                  {trade.side.toUpperCase()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-argus-text-dim">Shares</span>
                <span className="tabular-nums">{trade.shares}</span>
              </div>
              {trade.hold_duration_seconds != null && (
                <div className="flex justify-between col-span-2">
                  <span className="text-argus-text-dim flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Hold Duration
                  </span>
                  <span className="tabular-nums">{formatDuration(trade.hold_duration_seconds)}</span>
                </div>
              )}
              <div className="flex justify-between col-span-2">
                <span className="text-argus-text-dim">Commission</span>
                <span className="tabular-nums">{formatCurrency(trade.commission)}</span>
              </div>
              {trade.market_regime && (
                <div className="flex justify-between col-span-2">
                  <span className="text-argus-text-dim">Market Regime</span>
                  <span className="capitalize">{trade.market_regime}</span>
                </div>
              )}
            </div>
          </div>

          {/* Price Levels */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-argus-text-dim uppercase tracking-wider">Price Levels</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-argus-text-dim flex items-center gap-1">
                  <Shield className="w-3 h-3 text-argus-loss" />
                  Stop
                </span>
                <span className="tabular-nums text-argus-loss">
                  {trade.stop_price ? formatPrice(trade.stop_price) : '—'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-argus-text-dim flex items-center gap-1">
                  <Target className="w-3 h-3 text-argus-profit" />
                  T1
                </span>
                <span className="tabular-nums text-argus-profit">
                  {trade.target_prices?.[0] ? formatPrice(trade.target_prices[0]) : '—'}
                </span>
              </div>
              {trade.target_prices?.[1] && trade.target_prices[1] > 0 && (
                <div className="flex items-center justify-between col-span-2 justify-self-end">
                  <span className="text-argus-text-dim flex items-center gap-1">
                    <Target className="w-3 h-3 text-argus-profit" />
                    T2
                  </span>
                  <span className="tabular-nums text-argus-profit ml-4">
                    {formatPrice(trade.target_prices[1])}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </SlideInPanel>
  );
}
