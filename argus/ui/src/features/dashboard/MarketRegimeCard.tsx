/**
 * Market Regime Card for Dashboard.
 *
 * Sprint 18.75 Fix Session A:
 * - Shows current market regime with color-coded badge
 * - Displays supporting indicators from RegimeClassifier
 * - Uses orchestrator status API data
 */

import { useMemo } from 'react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { RegimeBadge } from '../../components/Badge';
import { useOrchestratorStatus } from '../../hooks';

// Regime display configuration
interface RegimeConfig {
  label: string;
  description: string;
}

const REGIME_CONFIG: Record<string, RegimeConfig> = {
  bullish: {
    label: 'Bullish Trending',
    description: 'Strong upward momentum',
  },
  bullish_trending: {
    label: 'Bullish Trending',
    description: 'Strong upward momentum',
  },
  bearish: {
    label: 'Bearish Trending',
    description: 'Strong downward momentum',
  },
  bearish_trending: {
    label: 'Bearish Trending',
    description: 'Strong downward momentum',
  },
  range: {
    label: 'Range-Bound',
    description: 'Consolidating in range',
  },
  range_bound: {
    label: 'Range-Bound',
    description: 'Consolidating in range',
  },
  high_vol: {
    label: 'High Volatility',
    description: 'Elevated volatility',
  },
  crisis: {
    label: 'Crisis Mode',
    description: 'Extreme conditions',
  },
};

// Indicator display names
const INDICATOR_LABELS: Record<string, string> = {
  volatility: 'Volatility',
  spy_vol_pct: 'SPY Vol',
  trend_score: 'Trend',
  momentum: 'Momentum',
  momentum_5d_roc: '5D ROC',
};

function formatIndicatorValue(key: string, value: number): string {
  if (key.includes('vol') || key.includes('pct')) {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (key.includes('score') || key.includes('momentum') || key.includes('roc')) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}`;
  }
  return value.toFixed(2);
}

function getIndicatorColor(key: string, value: number): string {
  if (key.includes('vol')) {
    // Higher vol = more concerning
    if (value > 0.25) return 'text-argus-loss';
    if (value > 0.15) return 'text-argus-warning';
    return 'text-argus-text-dim';
  }
  if (key.includes('trend') || key.includes('momentum') || key.includes('roc')) {
    if (value > 0.1) return 'text-argus-profit';
    if (value < -0.1) return 'text-argus-loss';
    return 'text-argus-text-dim';
  }
  return 'text-argus-text-dim';
}

export function MarketRegimeCard() {
  const { data: orchestratorData, isLoading } = useOrchestratorStatus();

  const { regime, regimeConfig, indicators } = useMemo(() => {
    if (!orchestratorData) {
      return { regime: null, regimeConfig: null, indicators: [] };
    }

    const normalizedRegime = orchestratorData.regime
      ?.toLowerCase()
      .replace(/[-\s]/g, '_');
    const config = normalizedRegime
      ? REGIME_CONFIG[normalizedRegime]
      : null;

    // Extract top 3 indicators for display
    const indicatorEntries = Object.entries(
      orchestratorData.regime_indicators || {}
    )
      .filter(([key]) => INDICATOR_LABELS[key])
      .slice(0, 3)
      .map(([key, value]) => ({
        key,
        label: INDICATOR_LABELS[key],
        value,
        formatted: formatIndicatorValue(key, value),
        color: getIndicatorColor(key, value),
      }));

    return {
      regime: orchestratorData.regime,
      regimeConfig: config,
      indicators: indicatorEntries,
    };
  }, [orchestratorData]);

  // Empty/loading state
  if (isLoading || !regime) {
    return (
      <Card className="h-full">
        <CardHeader title="Market Regime" />
        <div className="flex flex-col items-center justify-center h-full min-h-[120px] py-4">
          <span className="text-sm text-argus-text-dim text-center px-4">
            {isLoading
              ? 'Loading regime data...'
              : 'Regime data available during market hours'}
          </span>
        </div>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader title="Market Regime" />
      <div className="flex flex-col items-center py-4 space-y-4">
        {/* Hero badge */}
        <div className="flex flex-col items-center gap-2">
          <div className="scale-125">
            <RegimeBadge regime={regime} />
          </div>
          {regimeConfig && (
            <span className="text-xs text-argus-text-dim text-center">
              {regimeConfig.description}
            </span>
          )}
        </div>

        {/* Supporting indicators */}
        {indicators.length > 0 && (
          <div className="w-full px-4">
            <div className="grid grid-cols-3 gap-2 text-center">
              {indicators.map((ind) => (
                <div key={ind.key} className="space-y-0.5">
                  <div className="text-[10px] uppercase tracking-wide text-argus-text-dim">
                    {ind.label}
                  </div>
                  <div className={`text-sm font-medium tabular-nums ${ind.color}`}>
                    {ind.formatted}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Last updated */}
        {orchestratorData?.regime_updated_at && (
          <div className="text-[10px] text-argus-text-dim">
            Updated{' '}
            {new Date(orchestratorData.regime_updated_at).toLocaleTimeString(
              'en-US',
              { hour: 'numeric', minute: '2-digit' }
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

// Skeleton component for loading state
export function MarketRegimeSkeleton() {
  return (
    <Card className="h-full">
      <CardHeader title="Market Regime" />
      <div className="flex flex-col items-center py-4 space-y-4 animate-pulse">
        {/* Badge skeleton */}
        <div className="h-6 w-24 bg-argus-surface-2 rounded-full" />
        <div className="h-3 w-32 bg-argus-surface-2 rounded" />

        {/* Indicators skeleton */}
        <div className="w-full px-4">
          <div className="grid grid-cols-3 gap-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex flex-col items-center gap-1">
                <div className="h-2 w-12 bg-argus-surface-2 rounded" />
                <div className="h-4 w-10 bg-argus-surface-2 rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}
