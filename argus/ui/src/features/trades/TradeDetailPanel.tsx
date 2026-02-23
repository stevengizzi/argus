/**
 * Trade detail slide-in panel.
 *
 * Desktop: slides in from the right (40% width).
 * Mobile: slides up from the bottom (full screen).
 *
 * Shows comprehensive trade details including entry/exit, P&L, levels, and exit reason explanation.
 */

import { useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, TrendingUp, TrendingDown, Target, Shield, Clock } from 'lucide-react';
import { Badge } from '../../components/Badge';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import type { Trade } from '../../api/types';
import {
  formatCurrency,
  formatPrice,
  formatDuration,
  formatDateTime,
  formatPnl,
  formatPnlPercent,
  formatR,
} from '../../utils/format';
import { DURATION, EASE } from '../../utils/motion';

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
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const isOpen = trade !== null;

  // Close on Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    },
    [isOpen, onClose]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Prevent body scroll when panel is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Calculate P&L percentage if we have the data
  const pnlPercent =
    trade?.pnl_dollars != null && trade?.entry_price
      ? (trade.pnl_dollars / (trade.entry_price * trade.shares)) * 100
      : null;

  // Desktop: slide from right
  // Mobile: slide from bottom
  const panelVariants = {
    hidden: isDesktop ? { x: '100%' } : { y: '100%' },
    visible: isDesktop
      ? { x: 0, transition: { type: 'spring' as const, stiffness: 300, damping: 30 } }
      : { y: 0, transition: { type: 'spring' as const, stiffness: 300, damping: 30 } },
    exit: isDesktop
      ? { x: '100%', transition: { duration: DURATION.normal, ease: EASE.inOut } }
      : { y: '100%', transition: { duration: DURATION.normal, ease: EASE.inOut } },
  };

  const backdropVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: DURATION.fast } },
    exit: { opacity: 0, transition: { duration: DURATION.fast } },
  };

  return (
    <AnimatePresence>
      {isOpen && trade && (
        <>
          {/* Backdrop overlay */}
          <motion.div
            className="fixed inset-0 bg-black/60 z-40"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            className={`fixed z-50 bg-argus-surface border-argus-border overflow-y-auto ${
              isDesktop
                ? 'right-0 top-0 h-full w-[40%] min-w-[400px] max-w-[600px] border-l'
                : 'inset-x-0 bottom-0 h-[90vh] rounded-t-xl border-t'
            }`}
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            {/* Header */}
            <div className="sticky top-0 z-10 bg-argus-surface border-b border-argus-border px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xl font-semibold text-argus-text">{trade.symbol}</span>
                <Badge variant="info">{trade.strategy_id}</Badge>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-md hover:bg-argus-surface-2 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
                aria-label="Close panel"
              >
                <X className="w-5 h-5 text-argus-text-dim" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-6">
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

              {/* Price Levels placeholder - would need additional data from API */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-argus-text-dim uppercase tracking-wider">Price Levels</h3>
                <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-argus-text-dim flex items-center gap-1">
                      <Shield className="w-3 h-3 text-argus-loss" />
                      Stop
                    </span>
                    <span className="tabular-nums text-argus-loss">—</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-argus-text-dim flex items-center gap-1">
                      <Target className="w-3 h-3 text-argus-profit" />
                      T1
                    </span>
                    <span className="tabular-nums text-argus-profit">—</span>
                  </div>
                  <div className="flex items-center justify-between col-span-2 justify-self-end">
                    <span className="text-argus-text-dim flex items-center gap-1">
                      <Target className="w-3 h-3 text-argus-profit" />
                      T2
                    </span>
                    <span className="tabular-nums text-argus-profit ml-4">—</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
