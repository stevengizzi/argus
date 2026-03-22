/**
 * Unified strategy display configuration.
 *
 * Centralizes all strategy display metadata (names, colors, Tailwind classes)
 * to avoid duplication across components.
 *
 * IMPORTANT: Tailwind classes must be full static strings — dynamic class
 * construction (e.g., `border-l-${color}`) breaks Tailwind's purge.
 */

export interface StrategyDisplayConfig {
  /** Full strategy name (e.g., "ORB Breakout") */
  name: string;
  /** Shortened name for space-constrained displays (e.g., "ORB") */
  shortName: string;
  /** Single letter identifier (e.g., "O") */
  letter: string;
  /** Hex color for SVG/canvas usage */
  color: string;
  /** Tailwind color token (e.g., "blue-400") — for reference only, not for dynamic class construction */
  tailwindColor: string;
  /** Strategy ID for StrategyBadge component */
  badgeId: string;
}

/**
 * Strategy display configuration keyed by strategy_id.
 */
export const STRATEGY_DISPLAY: Record<string, StrategyDisplayConfig> = {
  strat_orb_breakout: {
    name: 'ORB Breakout',
    shortName: 'ORB',
    letter: 'O',
    color: '#60a5fa',
    tailwindColor: 'blue-400',
    badgeId: 'strat_orb_breakout',
  },
  strat_orb_scalp: {
    name: 'ORB Scalp',
    shortName: 'Scalp',
    letter: 'S',
    color: '#c084fc',
    tailwindColor: 'purple-400',
    badgeId: 'strat_orb_scalp',
  },
  strat_vwap_reclaim: {
    name: 'VWAP Reclaim',
    shortName: 'VWAP',
    letter: 'V',
    color: '#2dd4bf',
    tailwindColor: 'teal-400',
    badgeId: 'strat_vwap_reclaim',
  },
  strat_afternoon_momentum: {
    name: 'Afternoon Momentum',
    shortName: 'PM',
    letter: 'A',
    color: '#fbbf24',
    tailwindColor: 'amber-400',
    badgeId: 'strat_afternoon_momentum',
  },
  strat_red_to_green: {
    name: 'Red-to-Green',
    shortName: 'R2G',
    letter: 'R',
    color: '#fb923c',
    tailwindColor: 'orange-400',
    badgeId: 'strat_red_to_green',
  },
  strat_bull_flag: {
    name: 'Bull Flag',
    shortName: 'FLAG',
    letter: 'F',
    color: '#22d3ee',
    tailwindColor: 'cyan-400',
    badgeId: 'strat_bull_flag',
  },
  strat_flat_top_breakout: {
    name: 'Flat-Top Breakout',
    shortName: 'FLAT',
    letter: 'T',
    color: '#a78bfa',
    tailwindColor: 'violet-400',
    badgeId: 'strat_flat_top_breakout',
  },
};

/**
 * Tailwind border-left classes by strategy ID.
 * These must be full static strings for Tailwind purge to work.
 */
export const STRATEGY_BORDER_CLASSES: Record<string, string> = {
  strat_orb_breakout: 'border-l-blue-400',
  strat_orb_scalp: 'border-l-purple-400',
  strat_vwap_reclaim: 'border-l-teal-400',
  strat_afternoon_momentum: 'border-l-amber-400',
  strat_red_to_green: 'border-l-orange-400',
  strat_bull_flag: 'border-l-cyan-400',
  strat_flat_top_breakout: 'border-l-violet-400',
};

/**
 * Tailwind background classes by strategy ID.
 * These must be full static strings for Tailwind purge to work.
 */
export const STRATEGY_BAR_CLASSES: Record<string, string> = {
  strat_orb_breakout: 'bg-blue-400',
  strat_orb_scalp: 'bg-purple-400',
  strat_vwap_reclaim: 'bg-teal-400',
  strat_afternoon_momentum: 'bg-amber-400',
  strat_red_to_green: 'bg-orange-400',
  strat_bull_flag: 'bg-cyan-400',
  strat_flat_top_breakout: 'bg-violet-400',
};

/**
 * Get strategy display config with fallback for unknown strategies.
 * Handles both prefixed ('strat_orb_breakout') and non-prefixed ('orb_breakout') IDs.
 */
export function getStrategyDisplay(strategyId: string): StrategyDisplayConfig {
  // Normalize: lowercase, replace hyphens with underscores
  const normalizedId = strategyId.toLowerCase().replace(/-/g, '_');

  // Direct lookup first
  if (STRATEGY_DISPLAY[normalizedId]) {
    return STRATEGY_DISPLAY[normalizedId];
  }

  // Try with strat_ prefix if not already prefixed
  const prefixedId = normalizedId.startsWith('strat_') ? normalizedId : `strat_${normalizedId}`;
  if (STRATEGY_DISPLAY[prefixedId]) {
    return STRATEGY_DISPLAY[prefixedId];
  }

  // Grey fallback for unknown strategies: title-case the ID
  return {
    name: strategyId.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    shortName: strategyId.slice(0, 4).toUpperCase(),
    letter: strategyId.charAt(0).toUpperCase(),
    color: '#6b7280',
    tailwindColor: 'gray-400',
    badgeId: strategyId,
  };
}

/**
 * Normalize strategy ID to handle both prefixed and non-prefixed formats.
 */
function normalizeStrategyId(strategyId: string): string {
  const normalized = strategyId.toLowerCase().replace(/-/g, '_');
  return normalized.startsWith('strat_') ? normalized : `strat_${normalized}`;
}

/**
 * Get border-left class for a strategy with fallback.
 */
export function getStrategyBorderClass(strategyId: string): string {
  const normalized = normalizeStrategyId(strategyId);
  return STRATEGY_BORDER_CLASSES[normalized] ?? STRATEGY_BORDER_CLASSES[strategyId] ?? 'border-l-gray-400';
}

/**
 * Get background class for a strategy with fallback.
 */
export function getStrategyBarClass(strategyId: string): string {
  const normalized = normalizeStrategyId(strategyId);
  return STRATEGY_BAR_CLASSES[normalized] ?? STRATEGY_BAR_CLASSES[strategyId] ?? 'bg-gray-400';
}

/**
 * Get strategy hex color with fallback.
 */
export function getStrategyColor(strategyId: string): string {
  const normalized = normalizeStrategyId(strategyId);
  return STRATEGY_DISPLAY[normalized]?.color ?? STRATEGY_DISPLAY[strategyId]?.color ?? '#6b7280';
}
