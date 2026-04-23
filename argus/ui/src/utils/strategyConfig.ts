/**
 * Unified strategy display configuration.
 *
 * Centralizes all strategy display metadata (names, colors, Tailwind classes)
 * to avoid duplication across components. This module is the single source of
 * truth for strategy identity — `components/Badge.tsx` derives its maps from
 * the helpers exported here, and `ArenaCard.tsx` renders through the shared
 * `<StrategyBadge>` component rather than its own inline span.
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
    shortName: 'SCALP',
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
  strat_dip_and_rip: {
    name: 'Dip-and-Rip',
    shortName: 'DIP',
    letter: 'D',
    color: '#fb7185',
    tailwindColor: 'rose-400',
    badgeId: 'strat_dip_and_rip',
  },
  strat_hod_break: {
    name: 'HOD Break',
    shortName: 'HOD',
    letter: 'H',
    color: '#34d399',
    tailwindColor: 'emerald-400',
    badgeId: 'strat_hod_break',
  },
  strat_gap_and_go: {
    name: 'Gap-and-Go',
    shortName: 'GAP',
    letter: 'G',
    color: '#38bdf8',
    tailwindColor: 'sky-400',
    badgeId: 'strat_gap_and_go',
  },
  strat_abcd: {
    name: 'ABCD',
    shortName: 'ABCD',
    letter: 'X',
    color: '#f472b6',
    tailwindColor: 'pink-400',
    badgeId: 'strat_abcd',
  },
  strat_premarket_high_break: {
    name: 'PM High Break',
    shortName: 'PMH',
    letter: 'P',
    color: '#a3e635',
    tailwindColor: 'lime-400',
    badgeId: 'strat_premarket_high_break',
  },
  strat_micro_pullback: {
    name: 'Micro Pullback',
    shortName: 'MICRO',
    letter: 'M',
    color: '#818cf8',
    tailwindColor: 'indigo-400',
    badgeId: 'strat_micro_pullback',
  },
  strat_vwap_bounce: {
    name: 'VWAP Bounce',
    shortName: 'VWB',
    letter: 'B',
    color: '#e879f9',
    tailwindColor: 'fuchsia-400',
    badgeId: 'strat_vwap_bounce',
  },
  strat_narrow_range_breakout: {
    name: 'Narrow Range Breakout',
    shortName: 'NRB',
    letter: 'N',
    color: '#4ade80',
    tailwindColor: 'green-400',
    badgeId: 'strat_narrow_range_breakout',
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
  strat_dip_and_rip: 'border-l-rose-400',
  strat_hod_break: 'border-l-emerald-400',
  strat_gap_and_go: 'border-l-sky-400',
  strat_abcd: 'border-l-pink-400',
  strat_premarket_high_break: 'border-l-lime-400',
  strat_micro_pullback: 'border-l-indigo-400',
  strat_vwap_bounce: 'border-l-fuchsia-400',
  strat_narrow_range_breakout: 'border-l-green-400',
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
  strat_dip_and_rip: 'bg-rose-400',
  strat_hod_break: 'bg-emerald-400',
  strat_gap_and_go: 'bg-sky-400',
  strat_abcd: 'bg-pink-400',
  strat_premarket_high_break: 'bg-lime-400',
  strat_micro_pullback: 'bg-indigo-400',
  strat_vwap_bounce: 'bg-fuchsia-400',
  strat_narrow_range_breakout: 'bg-green-400',
};

/**
 * Tailwind badge (text + tinted background) classes by strategy ID.
 * Full static strings so Tailwind's purge keeps both `text-*-400` and
 * `bg-*-400/15` variants in the production bundle.
 */
export const STRATEGY_BADGE_CLASSES: Record<string, string> = {
  strat_orb_breakout: 'text-blue-400 bg-blue-400/15',
  strat_orb_scalp: 'text-purple-400 bg-purple-400/15',
  strat_vwap_reclaim: 'text-teal-400 bg-teal-400/15',
  strat_afternoon_momentum: 'text-amber-400 bg-amber-400/15',
  strat_red_to_green: 'text-orange-400 bg-orange-400/15',
  strat_bull_flag: 'text-cyan-400 bg-cyan-400/15',
  strat_flat_top_breakout: 'text-violet-400 bg-violet-400/15',
  strat_dip_and_rip: 'text-rose-400 bg-rose-400/15',
  strat_hod_break: 'text-emerald-400 bg-emerald-400/15',
  strat_gap_and_go: 'text-sky-400 bg-sky-400/15',
  strat_abcd: 'text-pink-400 bg-pink-400/15',
  strat_premarket_high_break: 'text-lime-400 bg-lime-400/15',
  strat_micro_pullback: 'text-indigo-400 bg-indigo-400/15',
  strat_vwap_bounce: 'text-fuchsia-400 bg-fuchsia-400/15',
  strat_narrow_range_breakout: 'text-green-400 bg-green-400/15',
};

/** Fallback badge class for unrecognized strategies. */
export const STRATEGY_FALLBACK_BADGE_CLASS = 'text-argus-text-dim bg-argus-surface-2';

/** High-contrast badge class used when the badge sits on an amber/yellow surface. */
export const STRATEGY_AMBER_BADGE_CLASS = 'text-white bg-slate-700';

/**
 * Legacy short-form strategy-id aliases. The Watchlist sidebar and some
 * older telemetry paths emit bare short names (`'orb'`, `'scalp'`,
 * `'vwap'`, `'momentum'`) rather than the canonical `strat_<full>` form.
 * The original `Badge.tsx` hand-coded these duplicates; now they resolve
 * through this single alias layer.
 */
const STRATEGY_LEGACY_ALIASES: Record<string, string> = {
  strat_orb: 'strat_orb_breakout',
  strat_scalp: 'strat_orb_scalp',
  strat_vwap: 'strat_vwap_reclaim',
  strat_momentum: 'strat_afternoon_momentum',
};

/**
 * Normalize strategy ID to the canonical `strat_<name>` form.
 * Lowercase, replaces hyphens, adds `strat_` prefix if missing, resolves
 * legacy short-form aliases.
 */
function normalizeStrategyId(strategyId: string): string {
  const normalized = strategyId.toLowerCase().replace(/-/g, '_');
  const prefixed = normalized.startsWith('strat_') ? normalized : `strat_${normalized}`;
  return STRATEGY_LEGACY_ALIASES[prefixed] ?? prefixed;
}

/**
 * Strip the variant suffix from an experiment-variant strategy ID to
 * recover the base strategy ID. Variant IDs use `__` as the structural
 * separator — e.g. `strat_bull_flag__v2_strong_pole` →
 * `strat_bull_flag`, `strat_dip_and_rip__v3_strict_volume` →
 * `strat_dip_and_rip`. See `config/experiments.yaml` + DEC-378 for the
 * canonical variant-id contract.
 *
 * IMPROMPTU-07 (2026-04-23): before this helper existed, variant IDs
 * fell through to the grey "unknown strategy" fallback in
 * `getStrategyDisplay`, so shadow variants showed up greyed-out in the
 * Command Center badges (Dashboard, Trades, Observatory) even though
 * they were active shadow positions.
 *
 * Delimiter-based (not pattern-match heuristic): any ID without the
 * `__` separator is returned unchanged, so base strategy IDs are
 * untouched.
 */
function stripVariantSuffix(strategyId: string): string {
  const idx = strategyId.indexOf('__');
  return idx >= 0 ? strategyId.slice(0, idx) : strategyId;
}

/**
 * Get strategy display config with fallback for unknown strategies.
 * Handles both prefixed ('strat_orb_breakout') and non-prefixed ('orb_breakout') IDs,
 * and resolves legacy short-form aliases ('orb', 'scalp', 'vwap', 'momentum').
 *
 * IMPROMPTU-07 (2026-04-23): also resolves experiment-variant IDs
 * (`strat_bull_flag__v2_strong_pole` etc.) by stripping the `__`
 * variant suffix and looking up the base strategy's display config, so
 * shadow variants share the base strategy's color and no longer render
 * as greyed-out "unknown strategy" badges across the Command Center.
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

  // Legacy short-form aliases (e.g. 'orb' → 'strat_orb_breakout')
  const aliasTarget = STRATEGY_LEGACY_ALIASES[prefixedId];
  if (aliasTarget && STRATEGY_DISPLAY[aliasTarget]) {
    return STRATEGY_DISPLAY[aliasTarget];
  }

  // Experiment-variant IDs (e.g. `strat_bull_flag__v2_strong_pole`):
  // strip the `__<variant>` suffix and try again against the base
  // strategy. Variant IDs use `__` as a structural separator (see
  // config/experiments.yaml). When we find the base, inherit its
  // color and short name but preserve the variant's full ID in badgeId.
  const baseId = stripVariantSuffix(prefixedId);
  if (baseId !== prefixedId && STRATEGY_DISPLAY[baseId]) {
    const base = STRATEGY_DISPLAY[baseId];
    return {
      ...base,
      badgeId: strategyId,
    };
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
 * Get border-left class for a strategy with fallback.
 * Resolves experiment-variant IDs to the base strategy's class
 * (IMPROMPTU-07: prevents variant badges greying out).
 */
export function getStrategyBorderClass(strategyId: string): string {
  const normalized = normalizeStrategyId(strategyId);
  const base = stripVariantSuffix(normalized);
  return (
    STRATEGY_BORDER_CLASSES[normalized]
    ?? STRATEGY_BORDER_CLASSES[base]
    ?? STRATEGY_BORDER_CLASSES[strategyId]
    ?? 'border-l-gray-400'
  );
}

/**
 * Get background class for a strategy with fallback.
 * Resolves experiment-variant IDs to the base strategy's class
 * (IMPROMPTU-07: prevents variant badges greying out).
 */
export function getStrategyBarClass(strategyId: string): string {
  const normalized = normalizeStrategyId(strategyId);
  const base = stripVariantSuffix(normalized);
  return (
    STRATEGY_BAR_CLASSES[normalized]
    ?? STRATEGY_BAR_CLASSES[base]
    ?? STRATEGY_BAR_CLASSES[strategyId]
    ?? 'bg-gray-400'
  );
}

/**
 * Get badge class (text + tinted background) for a strategy.
 * When `onAmber` is true, returns a high-contrast slate class suitable for
 * amber/yellow parent backgrounds instead of the strategy-specific tint.
 * Resolves experiment-variant IDs to the base strategy's class
 * (IMPROMPTU-07: prevents variant badges greying out).
 */
export function getStrategyBadgeClass(strategyId: string, onAmber = false): string {
  if (onAmber) return STRATEGY_AMBER_BADGE_CLASS;
  const normalized = normalizeStrategyId(strategyId);
  const base = stripVariantSuffix(normalized);
  return (
    STRATEGY_BADGE_CLASSES[normalized]
    ?? STRATEGY_BADGE_CLASSES[base]
    ?? STRATEGY_FALLBACK_BADGE_CLASS
  );
}

/**
 * Get strategy hex color with fallback. Resolves experiment-variant IDs
 * to the base strategy's color (IMPROMPTU-07).
 */
export function getStrategyColor(strategyId: string): string {
  const normalized = normalizeStrategyId(strategyId);
  const base = stripVariantSuffix(normalized);
  return (
    STRATEGY_DISPLAY[normalized]?.color
    ?? STRATEGY_DISPLAY[base]?.color
    ?? STRATEGY_DISPLAY[strategyId]?.color
    ?? '#6b7280'
  );
}

/** Get the short display label (e.g., "ORB", "PM", "VWB"). */
export function getStrategyShortName(strategyId: string): string {
  return getStrategyDisplay(strategyId).shortName;
}

/** Get the single-letter badge identifier (e.g., "O", "V", "M"). */
export function getStrategyLetter(strategyId: string): string {
  return getStrategyDisplay(strategyId).letter;
}

/** Get the full human-readable strategy name (e.g., "ORB Breakout"). */
export function getStrategyName(strategyId: string): string {
  return getStrategyDisplay(strategyId).name;
}
