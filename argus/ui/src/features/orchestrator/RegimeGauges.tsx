/**
 * Regime Gauges - visual gauge indicators for regime classification inputs.
 *
 * Replaces the text-based RegimeInputBreakdown with visual gauge bars.
 * Three gauges: Trend, Volatility, Momentum.
 * Each gauge shows a horizontal bar with positioned marker dot.
 */

import { useMemo } from 'react';
import type { OrchestratorStatusResponse } from '../../api/types';

interface RegimeGaugesProps {
  regimeIndicators: OrchestratorStatusResponse['regime_indicators'];
}

interface RegimeGaugeProps {
  label: string;
  value: number; // normalized 0-1 position on the gauge
  displayValue: string;
  interpretation: string;
  interpretationColor: string;
  leftLabel?: string;
  rightLabel?: string;
}

function RegimeGauge({
  label,
  value,
  displayValue,
  interpretation,
  interpretationColor,
  leftLabel,
  rightLabel,
}: RegimeGaugeProps) {
  // Clamp value to 0-1 range
  const clampedValue = Math.max(0, Math.min(1, value));

  // Determine marker color based on position
  const markerColor =
    clampedValue < 0.3 ? '#ef4444' : clampedValue < 0.7 ? '#f59e0b' : '#22c55e';

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-argus-text-dim font-medium w-12">{label}</span>
        <span className="text-argus-text tabular-nums text-xs flex-1 text-center">
          {displayValue}
        </span>
        <span className={`text-xs font-medium w-20 text-right ${interpretationColor}`}>
          {interpretation}
        </span>
      </div>
      <div className="relative h-2 rounded-full bg-argus-surface-2 overflow-hidden">
        {/* Gradient background: red → yellow → green */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: 'linear-gradient(to right, #ef4444, #f59e0b, #22c55e)',
            opacity: 0.3,
          }}
        />
        {/* Position marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-argus-bg shadow-sm"
          style={{
            left: `calc(${clampedValue * 100}% - 6px)`,
            backgroundColor: markerColor,
          }}
          data-testid={`gauge-marker-${label.toLowerCase()}`}
        />
      </div>
      {/* Scale labels */}
      {(leftLabel || rightLabel) && (
        <div className="flex justify-between text-[10px] text-argus-text-dim/50">
          <span>{leftLabel}</span>
          <span>{rightLabel}</span>
        </div>
      )}
    </div>
  );
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
function getMomentumLabel(roc: number): { label: string; color: string } {
  if (roc > 0.01) return { label: 'Bullish', color: 'text-argus-profit' };
  if (roc < -0.01) return { label: 'Bearish', color: 'text-argus-loss' };
  return { label: 'Neutral', color: 'text-argus-text-dim' };
}

// Trend score interpretation
function getTrendLabel(score: number): { label: string; color: string } {
  if (score >= 2) return { label: 'Strong Bull', color: 'text-argus-profit' };
  if (score >= 1) return { label: 'Bullish', color: 'text-argus-profit' };
  if (score <= -2) return { label: 'Strong Bear', color: 'text-argus-loss' };
  if (score <= -1) return { label: 'Bearish', color: 'text-argus-loss' };
  return { label: 'Neutral', color: 'text-argus-text-dim' };
}

function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`;
}

function formatPct(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(2)}%`;
}

export function RegimeGauges({ regimeIndicators }: RegimeGaugesProps) {
  const data = useMemo(() => {
    // Extract values from indicators (handle both naming conventions)
    const spyPrice = regimeIndicators?.spy_price ?? null;
    const sma20 = regimeIndicators?.spy_sma_20 ?? null;
    const sma50 = regimeIndicators?.spy_sma_50 ?? null;
    const vol = regimeIndicators?.spy_realized_vol_20d ?? regimeIndicators?.volatility ?? null;
    const roc = regimeIndicators?.spy_roc_5d ?? regimeIndicators?.momentum_5d_roc ?? null;

    // Compute trend score (above SMA = +1 each, below = -1 each)
    let trendScore = 0;
    if (spyPrice !== null && sma20 !== null) {
      trendScore += spyPrice > sma20 ? 1 : -1;
    }
    if (spyPrice !== null && sma50 !== null) {
      trendScore += spyPrice > sma50 ? 1 : -1;
    }

    // Normalize trend: score ranges -2 to +2, normalize to 0-1
    const trendNormalized = (trendScore + 2) / 4;

    // Normalize volatility: 0% to 50%+ annualized, INVERTED (low vol = good = right side)
    // 0% → 1.0, 50%+ → 0.0
    const volNormalized = vol !== null ? Math.max(0, Math.min(1, 1 - vol / 0.5)) : 0.5;

    // Normalize momentum: -5% to +5% ROC, normalize to 0-1
    const momNormalized = roc !== null ? Math.max(0, Math.min(1, (roc + 0.05) / 0.1)) : 0.5;

    return {
      spyPrice,
      vol,
      roc,
      trendScore,
      trendNormalized,
      volNormalized,
      momNormalized,
    };
  }, [regimeIndicators]);

  const hasData = data.spyPrice !== null || data.vol !== null || data.roc !== null;

  if (!hasData) {
    return <div className="text-sm text-argus-text-dim">Regime data unavailable</div>;
  }

  const trendLabel = getTrendLabel(data.trendScore);
  const volBucket = data.vol !== null ? getVolBucket(data.vol) : { label: '—', color: 'text-argus-text-dim' };
  const momentum = data.roc !== null ? getMomentumLabel(data.roc) : { label: '—', color: 'text-argus-text-dim' };

  return (
    <div className="flex flex-col gap-4">
      <RegimeGauge
        label="Trend"
        value={data.trendNormalized}
        displayValue={data.spyPrice !== null ? `SPY ${formatPrice(data.spyPrice)}` : '—'}
        interpretation={trendLabel.label}
        interpretationColor={trendLabel.color}
        leftLabel="Bear"
        rightLabel="Bull"
      />
      <RegimeGauge
        label="Vol"
        value={data.volNormalized}
        displayValue={data.vol !== null ? `${(data.vol * 100).toFixed(1)}% ann.` : '—'}
        interpretation={volBucket.label}
        interpretationColor={volBucket.color}
        leftLabel="Crisis"
        rightLabel="Calm"
      />
      <RegimeGauge
        label="Mom"
        value={data.momNormalized}
        displayValue={data.roc !== null ? `${formatPct(data.roc)} 5d ROC` : '—'}
        interpretation={momentum.label}
        interpretationColor={momentum.color}
        leftLabel="Bearish"
        rightLabel="Bullish"
      />
    </div>
  );
}
