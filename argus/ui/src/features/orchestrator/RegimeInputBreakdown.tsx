/**
 * Regime Input Breakdown - displays the inputs to regime classification.
 *
 * Three-row compact display showing:
 * - Trend: SPY price vs SMA-20 and SMA-50
 * - Volatility: Annualized vol with bucket label
 * - Momentum: 5-day ROC with directional indicator
 *
 * All thresholds match backend RegimeClassifier logic.
 */

import { useMemo } from 'react';
import { Check, X, Minus } from 'lucide-react';
import type { OrchestratorStatusResponse } from '../../api/types';

interface RegimeInputBreakdownProps {
  regimeIndicators: OrchestratorStatusResponse['regime_indicators'];
}

// Volatility bucket thresholds (annualized)
function getVolBucket(vol: number): { label: string; color: string } {
  if (vol < 0.08) return { label: 'Low', color: 'text-argus-profit' };
  if (vol < 0.16) return { label: 'Normal', color: 'text-argus-profit' };
  if (vol < 0.25) return { label: 'High', color: 'text-argus-warning' };
  if (vol < 0.35) return { label: 'Very High', color: 'text-orange-400' };
  return { label: 'Crisis', color: 'text-argus-loss' };
}

// Momentum interpretation
function getMomentumLabel(roc: number): { label: string; color: string; icon: 'check' | 'x' | 'minus' } {
  if (roc > 0.01) return { label: 'Bullish', color: 'text-argus-profit', icon: 'check' };
  if (roc < -0.01) return { label: 'Bearish', color: 'text-argus-loss', icon: 'x' };
  return { label: 'Neutral', color: 'text-argus-text-dim', icon: 'minus' };
}

// Trend score interpretation
function getTrendLabel(score: number): { label: string; color: string } {
  if (score >= 2) return { label: '+2 Strong Bull', color: 'text-argus-profit' };
  if (score >= 1) return { label: '+1 Bull', color: 'text-argus-profit' };
  if (score <= -2) return { label: '-2 Strong Bear', color: 'text-argus-loss' };
  if (score <= -1) return { label: '-1 Bear', color: 'text-argus-loss' };
  return { label: '0 Neutral', color: 'text-argus-text-dim' };
}

function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`;
}

function formatPct(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(2)}%`;
}

const IconMap = {
  check: Check,
  x: X,
  minus: Minus,
} as const;

export function RegimeInputBreakdown({ regimeIndicators }: RegimeInputBreakdownProps) {
  const data = useMemo(() => {
    // Extract values from indicators (handle both naming conventions)
    const spyPrice = regimeIndicators?.spy_price ?? null;
    const sma20 = regimeIndicators?.spy_sma_20 ?? null;
    const sma50 = regimeIndicators?.spy_sma_50 ?? null;
    const vol = regimeIndicators?.spy_realized_vol_20d ?? regimeIndicators?.volatility ?? null;
    const roc = regimeIndicators?.spy_roc_5d ?? regimeIndicators?.momentum_5d_roc ?? null;

    // Compute trend score (above SMA = +1 each)
    let trendScore = 0;
    const aboveSma20 = spyPrice !== null && sma20 !== null && spyPrice > sma20;
    const aboveSma50 = spyPrice !== null && sma50 !== null && spyPrice > sma50;
    if (aboveSma20) trendScore += 1;
    if (aboveSma50) trendScore += 1;
    const belowSma20 = spyPrice !== null && sma20 !== null && spyPrice < sma20;
    const belowSma50 = spyPrice !== null && sma50 !== null && spyPrice < sma50;
    if (belowSma20) trendScore -= 1;
    if (belowSma50) trendScore -= 1;

    return {
      spyPrice,
      sma20,
      sma50,
      vol,
      roc,
      trendScore,
      aboveSma20,
      aboveSma50,
    };
  }, [regimeIndicators]);

  const hasData = data.spyPrice !== null || data.vol !== null || data.roc !== null;

  if (!hasData) {
    return (
      <div className="text-sm text-argus-text-dim">
        Regime data unavailable
      </div>
    );
  }

  const volBucket = data.vol !== null ? getVolBucket(data.vol) : null;
  const momentum = data.roc !== null ? getMomentumLabel(data.roc) : null;
  const trendLabel = getTrendLabel(data.trendScore);
  const MomentumIcon = momentum ? IconMap[momentum.icon] : null;

  return (
    <div className="space-y-2 text-sm">
      {/* Row 1: Trend */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-argus-text-dim font-medium w-16 shrink-0">Trend</span>
        {data.spyPrice !== null ? (
          <>
            <span className="text-argus-text tabular-nums">SPY {formatPrice(data.spyPrice)}</span>
            {data.sma20 !== null && (
              <span className={`flex items-center gap-1 ${data.aboveSma20 ? 'text-argus-profit' : 'text-argus-loss'}`}>
                {data.aboveSma20 ? (
                  <Check className="w-3 h-3" />
                ) : (
                  <X className="w-3 h-3" />
                )}
                <span className="text-argus-text-dim text-xs">SMA-20</span>
                <span className="tabular-nums text-xs">{formatPrice(data.sma20)}</span>
              </span>
            )}
            {data.sma50 !== null && (
              <span className={`flex items-center gap-1 ${data.aboveSma50 ? 'text-argus-profit' : 'text-argus-loss'}`}>
                {data.aboveSma50 ? (
                  <Check className="w-3 h-3" />
                ) : (
                  <X className="w-3 h-3" />
                )}
                <span className="text-argus-text-dim text-xs">SMA-50</span>
                <span className="tabular-nums text-xs">{formatPrice(data.sma50)}</span>
              </span>
            )}
            <span className={`text-xs font-medium ${trendLabel.color}`}>
              {trendLabel.label}
            </span>
          </>
        ) : (
          <span className="text-argus-text-dim">—</span>
        )}
      </div>

      {/* Row 2: Volatility */}
      <div className="flex items-center gap-2">
        <span className="text-argus-text-dim font-medium w-16 shrink-0">Vol</span>
        {data.vol !== null && volBucket ? (
          <>
            <span className="text-argus-text tabular-nums">{(data.vol * 100).toFixed(1)}% ann.</span>
            <span className={`text-xs font-medium ${volBucket.color}`}>
              {volBucket.label}
            </span>
          </>
        ) : (
          <span className="text-argus-text-dim">—</span>
        )}
      </div>

      {/* Row 3: Momentum */}
      <div className="flex items-center gap-2">
        <span className="text-argus-text-dim font-medium w-16 shrink-0">Mom</span>
        {data.roc !== null && momentum && MomentumIcon ? (
          <>
            <span className="text-argus-text tabular-nums">{formatPct(data.roc)} 5d ROC</span>
            <span className={`flex items-center gap-1 text-xs font-medium ${momentum.color}`}>
              <MomentumIcon className="w-3 h-3" />
              {momentum.label}
            </span>
          </>
        ) : (
          <span className="text-argus-text-dim">—</span>
        )}
      </div>
    </div>
  );
}
