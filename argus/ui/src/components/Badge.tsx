/**
 * Badge component with semantic variants.
 *
 * Extended variants (17-D from UX Feature Backlog):
 * - exit_reason: existing T1, T2, SL, TIME, EOD badges
 * - strategy: ORB=blue, Scalp=purple, VWAP=teal, Momentum=amber
 * - regime: Bullish=green, Bearish=red, Range=yellow, HighVol=orange, Crisis=red-600
 * - risk: Normal=green, Approaching=yellow, AtLimit=red
 * - throttle: Active=green, Reduced=yellow, Suspended=red
 */

// Base variant types (original)
type BaseVariant = 'info' | 'success' | 'warning' | 'danger' | 'neutral';

// Strategy identifiers
type StrategyId = 'orb' | 'orb_breakout' | 'scalp' | 'orb_scalp' | 'vwap' | 'vwap_reclaim' | 'momentum' | 'afternoon_momentum';

// Market regime identifiers
type RegimeId = 'bullish' | 'bullish_trending' | 'bearish' | 'bearish_trending' | 'range' | 'range_bound' | 'high_vol' | 'crisis';

// Risk level identifiers
type RiskLevelId = 'normal' | 'approaching' | 'at_limit';

// Throttle status identifiers
type ThrottleId = 'active' | 'reduced' | 'suspended';

// Color mapping for strategies
const strategyColors: Record<StrategyId, string> = {
  orb: 'text-blue-400 bg-blue-400/15',
  orb_breakout: 'text-blue-400 bg-blue-400/15',
  scalp: 'text-purple-400 bg-purple-400/15',
  orb_scalp: 'text-purple-400 bg-purple-400/15',
  vwap: 'text-teal-400 bg-teal-400/15',
  vwap_reclaim: 'text-teal-400 bg-teal-400/15',
  momentum: 'text-amber-400 bg-amber-400/15',
  afternoon_momentum: 'text-amber-400 bg-amber-400/15',
};

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

// Display labels for strategies
const strategyLabels: Record<string, string> = {
  orb: 'ORB',
  orb_breakout: 'ORB',
  scalp: 'SCALP',
  orb_scalp: 'SCALP',
  vwap: 'VWAP',
  vwap_reclaim: 'VWAP',
  momentum: 'MOM',
  afternoon_momentum: 'MOM',
};

// Single-letter labels for compact badges
const strategyLetters: Record<string, string> = {
  orb: 'O',
  orb_breakout: 'O',
  scalp: 'S',
  orb_scalp: 'S',
  vwap: 'V',
  vwap_reclaim: 'V',
  momentum: 'A', // Afternoon Momentum → A
  afternoon_momentum: 'A',
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

// Strategy badge - shows strategy type with color coding
export function StrategyBadge({ strategyId, onAmber = false }: StrategyBadgeProps) {
  // Normalize: lowercase, replace hyphens, strip "strat_" prefix
  const normalizedId = strategyId.toLowerCase().replace(/-/g, '_').replace(/^strat_/, '') as StrategyId;
  const label = strategyLabels[normalizedId] || strategyId.toUpperCase().slice(0, 4);

  // On amber backgrounds, use dark bg with white text for contrast
  const colorClass = onAmber
    ? 'text-white bg-slate-700'
    : strategyColors[normalizedId] || 'text-argus-text-dim bg-argus-surface-2';

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  );
}

// Compact strategy badge - single-letter pill for dense layouts (watchlist sidebar)
export function CompactStrategyBadge({ strategyId }: { strategyId: string }) {
  // Normalize: lowercase, replace hyphens, strip "strat_" prefix
  const normalizedId = strategyId.toLowerCase().replace(/-/g, '_').replace(/^strat_/, '') as StrategyId;
  const letter = strategyLetters[normalizedId] || strategyId.charAt(0).toUpperCase();
  const colorClass = strategyColors[normalizedId] || 'text-argus-text-dim bg-argus-surface-2';

  return (
    <span
      className={`inline-flex items-center justify-center w-5 h-[18px] rounded-full text-xs font-semibold ${colorClass}`}
      title={strategyLabels[normalizedId] || strategyId}
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
