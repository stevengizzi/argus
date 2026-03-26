/**
 * VIX Regime Card for the Dashboard.
 *
 * Displays current VIX close, VRP tier, vol regime phase, and momentum arrow.
 * Returns null when VIX is disabled or unavailable (no layout shift).
 *
 * Sprint 27.9, Session 4.
 */

import { Activity } from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { useVixData } from '../../hooks';

/** Color mapping for VRP tier badges. */
const VRP_COLORS: Record<string, string> = {
  COMPRESSED: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  NORMAL: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  ELEVATED: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  EXTREME: 'bg-red-500/20 text-red-400 border-red-500/30',
};

/** Color mapping for vol regime phase labels. */
const PHASE_COLORS: Record<string, string> = {
  CALM: 'text-emerald-400',
  TRANSITION: 'text-yellow-400',
  VOL_EXPANSION: 'text-orange-400',
  CRISIS: 'text-red-400',
};

/** Momentum arrow display mapping. */
const MOMENTUM_DISPLAY: Record<string, { arrow: string; color: string }> = {
  STABILIZING: { arrow: '\u2191', color: 'text-emerald-400' },
  NEUTRAL: { arrow: '\u2192', color: 'text-argus-text-dim' },
  DETERIORATING: { arrow: '\u2193', color: 'text-red-400' },
};

/** Format data_date to short label (e.g., "Mar 25"). */
function formatDateLabel(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/** Skeleton placeholder for loading state. */
function VixRegimeCardSkeleton() {
  return (
    <Card className="h-full">
      <CardHeader title="VIX Regime" />
      <div className="animate-pulse space-y-3">
        <div className="h-8 bg-argus-surface-2 rounded w-28" />
        <div className="h-5 bg-argus-surface-2 rounded w-20" />
        <div className="h-4 bg-argus-surface-2 rounded w-24" />
        <div className="h-4 bg-argus-surface-2 rounded w-16" />
      </div>
    </Card>
  );
}

export function VixRegimeCard() {
  const { data, isLoading } = useVixData();

  // Loading state
  if (isLoading) {
    return <VixRegimeCardSkeleton />;
  }

  // Hidden when disabled or unavailable
  if (!data || data.status === 'unavailable') {
    return null;
  }

  const isStale = data.is_stale === true;
  const regime = data.regime;
  const vrpTier = regime?.vrp_tier?.toUpperCase() ?? null;
  const volPhase = regime?.vol_regime_phase?.toUpperCase() ?? null;
  const momentum = regime?.vol_regime_momentum?.toUpperCase() ?? null;
  const momentumDisplay = momentum ? MOMENTUM_DISPLAY[momentum] : null;

  // Status indicator dot
  const statusDot = isStale
    ? 'bg-yellow-400'
    : 'bg-emerald-400';

  return (
    <Card className="h-full">
      <CardHeader
        title="VIX Regime"
        icon={<Activity className="w-4 h-4 text-argus-text-dim" />}
        badge={
          <div className="flex items-center gap-1.5">
            {isStale && (
              <span
                className="text-[10px] uppercase tracking-wider font-medium
                  text-yellow-400 bg-yellow-500/15 border border-yellow-500/30
                  px-1.5 py-0.5 rounded"
                data-testid="stale-badge"
              >
                Stale
              </span>
            )}
            <span
              className={`w-2 h-2 rounded-full ${statusDot}`}
              data-testid="status-dot"
            />
          </div>
        }
      />

      {/* VIX Close */}
      <div className={`mb-3 ${isStale ? 'opacity-60' : ''}`}>
        <div className="flex items-baseline gap-2">
          <span
            className="text-3xl font-semibold text-argus-text tabular-nums"
            data-testid="vix-close"
          >
            {data.vix_close != null ? data.vix_close.toFixed(2) : '--'}
          </span>
          {data.data_date && (
            <span className="text-xs text-argus-text-dim">
              ({formatDateLabel(data.data_date)})
            </span>
          )}
        </div>
        <div className="text-xs text-argus-text-dim">VIX Close</div>
      </div>

      {/* VRP Tier */}
      {vrpTier && (
        <div className={`mb-2 ${isStale ? 'opacity-60' : ''}`}>
          <span
            className={`text-xs font-medium uppercase tracking-wider px-2 py-0.5
              rounded border ${VRP_COLORS[vrpTier] ?? 'bg-argus-surface-2 text-argus-text-dim border-argus-border'}`}
            data-testid="vrp-tier"
          >
            VRP: {vrpTier}
          </span>
        </div>
      )}

      {/* Vol Regime Phase + Momentum */}
      <div className={`flex items-center justify-between text-sm ${isStale ? 'opacity-60' : ''}`}>
        {volPhase && (
          <span
            className={`font-medium ${PHASE_COLORS[volPhase] ?? 'text-argus-text-dim'}`}
            data-testid="vol-phase"
          >
            {volPhase.replace('_', ' ')}
          </span>
        )}
        {momentumDisplay && (
          <span
            className={`text-lg font-bold ${momentumDisplay.color}`}
            data-testid="momentum-arrow"
            title={momentum ?? ''}
          >
            {momentumDisplay.arrow}
          </span>
        )}
      </div>
    </Card>
  );
}
