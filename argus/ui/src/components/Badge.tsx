/**
 * Badge component with semantic variants.
 *
 * Strategy identity (colors, short labels, single letters) is derived from
 * `utils/strategyConfig.ts` — the single source of truth. This module only
 * owns regime / risk / throttle / base-variant styling.
 *
 * Variants:
 * - base: info / success / warning / danger / neutral
 * - strategy: colors + short labels resolved via strategyConfig
 * - regime: Bullish=green, Bearish=red, Range=yellow, HighVol=orange, Crisis=red-600
 * - risk: Normal=green, Approaching=yellow, AtLimit=red
 * - throttle: Active=green, Reduced=yellow, Suspended=red
 */

import {
  getStrategyBadgeClass,
  getStrategyLetter,
  getStrategyShortName,
} from '../utils/strategyConfig';

// Base variant types (original)
type BaseVariant = 'info' | 'success' | 'warning' | 'danger' | 'neutral';

// Market regime identifiers
type RegimeId = 'bullish' | 'bullish_trending' | 'bearish' | 'bearish_trending' | 'range' | 'range_bound' | 'high_vol' | 'crisis';

// Risk level identifiers
type RiskLevelId = 'normal' | 'approaching' | 'at_limit';

// Throttle status identifiers
type ThrottleId = 'active' | 'reduced' | 'suspended';

// Color mapping for market regimes
const regimeColors: Record<RegimeId, string> = {
  bullish: 'text-argus-profit bg-argus-profit-dim',
  bullish_trending: 'text-argus-profit bg-argus-profit-dim',
  bearish: 'text-argus-loss bg-argus-loss-dim',
  bearish_trending: 'text-argus-loss bg-argus-loss-dim',
  range: 'text-argus-warning bg-argus-warning-dim',
  range_bound: 'text-argus-warning bg-argus-warning-dim',
  high_vol: 'text-orange-400 bg-orange-400/15',
  crisis: 'text-red-500 bg-red-500/15',
};

// Color mapping for risk levels
const riskColors: Record<RiskLevelId, string> = {
  normal: 'text-argus-profit bg-argus-profit-dim',
  approaching: 'text-argus-warning bg-argus-warning-dim',
  at_limit: 'text-argus-loss bg-argus-loss-dim',
};

// Color mapping for throttle status
const throttleColors: Record<ThrottleId, string> = {
  active: 'text-argus-profit bg-argus-profit-dim',
  reduced: 'text-argus-warning bg-argus-warning-dim',
  suspended: 'text-argus-loss bg-argus-loss-dim',
};

// Base variant colors (original)
const baseVariantClasses: Record<BaseVariant, string> = {
  info: 'text-argus-accent bg-argus-accent/15',
  success: 'text-argus-profit bg-argus-profit-dim',
  warning: 'text-argus-warning bg-argus-warning-dim',
  danger: 'text-argus-loss bg-argus-loss-dim',
  neutral: 'text-argus-text-dim bg-argus-surface-2',
};

// Display labels for regimes
const regimeLabels: Record<string, string> = {
  bullish: 'Bullish',
  bullish_trending: 'Bullish',
  bearish: 'Bearish',
  bearish_trending: 'Bearish',
  range: 'Range',
  range_bound: 'Range',
  high_vol: 'High Vol',
  crisis: 'Crisis',
};

// Display labels for risk levels
const riskLabels: Record<string, string> = {
  normal: 'Normal',
  approaching: 'Near Limit',
  at_limit: 'At Limit',
};

// Display labels for throttle status
const throttleLabels: Record<string, string> = {
  active: 'Active',
  reduced: 'Reduced',
  suspended: 'Suspended',
};

interface BaseBadgeProps {
  children: React.ReactNode;
  variant: BaseVariant;
}

interface StrategyBadgeProps {
  strategyId: string;
  /** Use high-contrast styling for amber/yellow backgrounds */
  onAmber?: boolean;
  /** Optional test hook — passed through to the rendered span. */
  'data-testid'?: string;
}

interface RegimeBadgeProps {
  regime: string;
}

interface RiskBadgeProps {
  riskLevel: string;
}

interface ThrottleBadgeProps {
  throttleStatus: string;
}

// Original Badge component (unchanged API)
export function Badge({ children, variant }: BaseBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${baseVariantClasses[variant]}`}
    >
      {children}
    </span>
  );
}

// Strategy badge - shows strategy type with color coding derived from strategyConfig.
export function StrategyBadge({
  strategyId,
  onAmber = false,
  'data-testid': testId,
}: StrategyBadgeProps) {
  const label = getStrategyShortName(strategyId);
  const colorClass = getStrategyBadgeClass(strategyId, onAmber);

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}
      data-testid={testId}
    >
      {label}
    </span>
  );
}

// Compact strategy badge - single-letter pill for dense layouts (watchlist sidebar).
// Title is the short label (e.g. "ORB", "SCALP") so dense hover tooltips stay
// compact and match the main StrategyBadge's visible text.
export function CompactStrategyBadge({ strategyId }: { strategyId: string }) {
  const letter = getStrategyLetter(strategyId);
  const colorClass = getStrategyBadgeClass(strategyId);

  return (
    <span
      className={`inline-flex items-center justify-center w-5 h-[18px] rounded-full text-xs font-semibold ${colorClass}`}
      title={getStrategyShortName(strategyId)}
    >
      {letter}
    </span>
  );
}

// Market regime badge - shows current market conditions
export function RegimeBadge({ regime }: RegimeBadgeProps) {
  const normalizedRegime = regime.toLowerCase().replace(/[-\s]/g, '_') as RegimeId;
  const colorClass = regimeColors[normalizedRegime] || 'text-argus-text-dim bg-argus-surface-2';
  const label = regimeLabels[normalizedRegime] || regime;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  );
}

// Risk level badge - shows risk utilization status
export function RiskBadge({ riskLevel }: RiskBadgeProps) {
  const normalizedLevel = riskLevel.toLowerCase().replace(/[-\s]/g, '_') as RiskLevelId;
  const colorClass = riskColors[normalizedLevel] || 'text-argus-text-dim bg-argus-surface-2';
  const label = riskLabels[normalizedLevel] || riskLevel;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  );
}

// Throttle status badge - shows system throttling state
export function ThrottleBadge({ throttleStatus }: ThrottleBadgeProps) {
  const normalizedStatus = throttleStatus.toLowerCase().replace(/[-\s]/g, '_') as ThrottleId;
  const colorClass = throttleColors[normalizedStatus] || 'text-argus-text-dim bg-argus-surface-2';
  const label = throttleLabels[normalizedStatus] || throttleStatus;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  );
}
