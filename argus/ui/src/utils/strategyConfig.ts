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
  orb_breakout: {
    name: 'ORB Breakout',
    shortName: 'ORB',
    letter: 'O',
    color: '#60a5fa',
    tailwindColor: 'blue-400',
    badgeId: 'orb_breakout',
  },
  orb_scalp: {
    name: 'ORB Scalp',
    shortName: 'Scalp',
    letter: 'S',
    color: '#c084fc',
    tailwindColor: 'purple-400',
    badgeId: 'orb_scalp',
  },
  vwap_reclaim: {
    name: 'VWAP Reclaim',
    shortName: 'VWAP',
    letter: 'V',
    color: '#2dd4bf',
    tailwindColor: 'teal-400',
    badgeId: 'vwap_reclaim',
  },
  afternoon_momentum: {
    name: 'Afternoon Momentum',
    shortName: 'PM',
    letter: 'A',
    color: '#fbbf24',
    tailwindColor: 'amber-400',
    badgeId: 'afternoon_momentum',
  },
};

/**
 * Tailwind border-left classes by strategy ID.
 * These must be full static strings for Tailwind purge to work.
 */
export const STRATEGY_BORDER_CLASSES: Record<string, string> = {
  orb_breakout: 'border-l-blue-400',
  orb_scalp: 'border-l-purple-400',
  vwap_reclaim: 'border-l-teal-400',
  afternoon_momentum: 'border-l-amber-400',
};

/**
 * Tailwind background classes by strategy ID.
 * These must be full static strings for Tailwind purge to work.
 */
export const STRATEGY_BAR_CLASSES: Record<string, string> = {
  orb_breakout: 'bg-blue-400',
  orb_scalp: 'bg-purple-400',
  vwap_reclaim: 'bg-teal-400',
  afternoon_momentum: 'bg-amber-400',
};

/**
 * Get strategy display config with fallback for unknown strategies.
 */
export function getStrategyDisplay(strategyId: string): StrategyDisplayConfig {
  const config = STRATEGY_DISPLAY[strategyId];
  if (config) {
    return config;
  }

  // Fallback for unknown strategies: title-case the ID
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
 * Get border-left class for a strategy with fallback.
 */
export function getStrategyBorderClass(strategyId: string): string {
  return STRATEGY_BORDER_CLASSES[strategyId] ?? 'border-l-gray-400';
}

/**
 * Get background class for a strategy with fallback.
 */
export function getStrategyBarClass(strategyId: string): string {
  return STRATEGY_BAR_CLASSES[strategyId] ?? 'bg-gray-400';
}

/**
 * Get strategy hex color with fallback.
 */
export function getStrategyColor(strategyId: string): string {
  return STRATEGY_DISPLAY[strategyId]?.color ?? '#6b7280';
}
