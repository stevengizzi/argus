/**
 * Tests for strategyConfig utility functions.
 *
 * Sprint 21.5.1, Session 3.
 */

import { describe, it, expect } from 'vitest';
import {
  STRATEGY_DISPLAY,
  STRATEGY_BADGE_CLASSES,
  STRATEGY_BAR_CLASSES,
  STRATEGY_BORDER_CLASSES,
  STRATEGY_AMBER_BADGE_CLASS,
  getStrategyDisplay,
  getStrategyColor,
  getStrategyBorderClass,
  getStrategyBarClass,
  getStrategyBadgeClass,
  getStrategyLetter,
  getStrategyShortName,
  getStrategyName,
} from './strategyConfig';

describe('strategyConfig', () => {
  describe('getStrategyDisplay', () => {
    it('returns correct config for strat_ prefixed strategy IDs', () => {
      const orbConfig = getStrategyDisplay('strat_orb_breakout');

      expect(orbConfig.name).toBe('ORB Breakout');
      expect(orbConfig.shortName).toBe('ORB');
      expect(orbConfig.letter).toBe('O');
      expect(orbConfig.color).toBe('#60a5fa');
      expect(orbConfig.badgeId).toBe('strat_orb_breakout');
    });

    it('returns correct config for non-prefixed strategy IDs', () => {
      // Should find orb_breakout by adding strat_ prefix
      const orbConfig = getStrategyDisplay('orb_breakout');
      expect(orbConfig.name).toBe('ORB Breakout');
      expect(orbConfig.letter).toBe('O');

      // Should find orb_scalp by adding strat_ prefix
      const scalpConfig = getStrategyDisplay('orb_scalp');
      expect(scalpConfig.name).toBe('ORB Scalp');
      expect(scalpConfig.letter).toBe('S');
    });

    it('returns correct config for all known strategies', () => {
      expect(getStrategyDisplay('strat_orb_scalp').name).toBe('ORB Scalp');
      expect(getStrategyDisplay('strat_vwap_reclaim').name).toBe('VWAP Reclaim');
      expect(getStrategyDisplay('strat_afternoon_momentum').name).toBe('Afternoon Momentum');
      expect(getStrategyDisplay('strat_red_to_green').name).toBe('Red-to-Green');
      expect(getStrategyDisplay('strat_bull_flag').name).toBe('Bull Flag');
      expect(getStrategyDisplay('strat_flat_top_breakout').name).toBe('Flat-Top Breakout');
      expect(getStrategyDisplay('strat_dip_and_rip').name).toBe('Dip-and-Rip');
      expect(getStrategyDisplay('strat_hod_break').name).toBe('HOD Break');
      expect(getStrategyDisplay('strat_gap_and_go').name).toBe('Gap-and-Go');
      expect(getStrategyDisplay('strat_abcd').name).toBe('ABCD');
      expect(getStrategyDisplay('strat_premarket_high_break').name).toBe('PM High Break');
    });

    it('returns correct short names for new strategies', () => {
      expect(getStrategyDisplay('strat_red_to_green').shortName).toBe('R2G');
      expect(getStrategyDisplay('strat_bull_flag').shortName).toBe('FLAG');
      expect(getStrategyDisplay('strat_flat_top_breakout').shortName).toBe('FLAT');
      expect(getStrategyDisplay('strat_dip_and_rip').shortName).toBe('DIP');
      expect(getStrategyDisplay('strat_hod_break').shortName).toBe('HOD');
      expect(getStrategyDisplay('strat_gap_and_go').shortName).toBe('GAP');
      expect(getStrategyDisplay('strat_abcd').shortName).toBe('ABCD');
      expect(getStrategyDisplay('strat_premarket_high_break').shortName).toBe('PMH');
    });

    it('returns correct config for all 12 strategy IDs with strat_ prefix', () => {
      const allStrategyIds = [
        'strat_orb_breakout',
        'strat_orb_scalp',
        'strat_vwap_reclaim',
        'strat_afternoon_momentum',
        'strat_red_to_green',
        'strat_bull_flag',
        'strat_flat_top_breakout',
        'strat_dip_and_rip',
        'strat_hod_break',
        'strat_gap_and_go',
        'strat_abcd',
        'strat_premarket_high_break',
      ];
      for (const id of allStrategyIds) {
        const config = getStrategyDisplay(id);
        // All known strategies must have a non-grey color
        expect(config.color).not.toBe('#6b7280');
        // badgeId must match the input
        expect(config.badgeId).toBe(id);
      }
    });

    it('returns correct config for all 12 strategy IDs without strat_ prefix', () => {
      const nonPrefixedIds = [
        'orb_breakout',
        'orb_scalp',
        'vwap_reclaim',
        'afternoon_momentum',
        'red_to_green',
        'bull_flag',
        'flat_top_breakout',
        'dip_and_rip',
        'hod_break',
        'gap_and_go',
        'abcd',
        'premarket_high_break',
      ];
      for (const id of nonPrefixedIds) {
        const config = getStrategyDisplay(id);
        // All known strategies must have a non-grey color
        expect(config.color).not.toBe('#6b7280');
      }
    });

    it('returns correct config for Sprint 31A strategies (audit FIX-12 P1-F2-C01)', () => {
      const microPullback = getStrategyDisplay('strat_micro_pullback');
      expect(microPullback.name).toBe('Micro Pullback');
      expect(microPullback.shortName).toBe('MICRO');
      expect(microPullback.letter).toBe('M');
      expect(microPullback.color).toBe('#818cf8');
      expect(microPullback.tailwindColor).toBe('indigo-400');

      const vwapBounce = getStrategyDisplay('strat_vwap_bounce');
      expect(vwapBounce.name).toBe('VWAP Bounce');
      expect(vwapBounce.shortName).toBe('VWB');
      expect(vwapBounce.letter).toBe('B');
      expect(vwapBounce.color).toBe('#e879f9');
      expect(vwapBounce.tailwindColor).toBe('fuchsia-400');

      const narrowRange = getStrategyDisplay('strat_narrow_range_breakout');
      expect(narrowRange.name).toBe('Narrow Range Breakout');
      expect(narrowRange.shortName).toBe('NRB');
      expect(narrowRange.letter).toBe('N');
      expect(narrowRange.color).toBe('#4ade80');
      expect(narrowRange.tailwindColor).toBe('green-400');
    });

    it('all 15 live-universe strategies have non-grey color + unique letter', () => {
      const liveStrategyIds = [
        'strat_orb_breakout',
        'strat_orb_scalp',
        'strat_vwap_reclaim',
        'strat_afternoon_momentum',
        'strat_red_to_green',
        'strat_bull_flag',
        'strat_flat_top_breakout',
        'strat_dip_and_rip',
        'strat_hod_break',
        'strat_gap_and_go',
        'strat_abcd',
        'strat_premarket_high_break',
        'strat_micro_pullback',
        'strat_vwap_bounce',
        'strat_narrow_range_breakout',
      ];
      const seenLetters = new Set<string>();
      const seenShortNames = new Set<string>();
      for (const id of liveStrategyIds) {
        const config = getStrategyDisplay(id);
        expect(config.color, `${id} must not be grey`).not.toBe('#6b7280');
        expect(seenLetters.has(config.letter), `letter ${config.letter} duplicated at ${id}`).toBe(
          false,
        );
        expect(
          seenShortNames.has(config.shortName),
          `shortName ${config.shortName} duplicated at ${id}`,
        ).toBe(false);
        seenLetters.add(config.letter);
        seenShortNames.add(config.shortName);
      }
      expect(seenLetters.size).toBe(15);
      expect(seenShortNames.size).toBe(15);
    });

    it('STRATEGY_DISPLAY, border/bar/badge maps all cover the same keys (single source of truth)', () => {
      const displayKeys = Object.keys(STRATEGY_DISPLAY).sort();
      expect(Object.keys(STRATEGY_BORDER_CLASSES).sort()).toEqual(displayKeys);
      expect(Object.keys(STRATEGY_BAR_CLASSES).sort()).toEqual(displayKeys);
      expect(Object.keys(STRATEGY_BADGE_CLASSES).sort()).toEqual(displayKeys);
    });

    it('returns grey fallback for unknown strategies', () => {
      const unknownConfig = getStrategyDisplay('unknown_strategy');

      // Should use grey color fallback
      expect(unknownConfig.color).toBe('#6b7280');
      expect(unknownConfig.tailwindColor).toBe('gray-400');
      // Name should be title-cased from the ID
      expect(unknownConfig.name).toBe('Unknown Strategy');
      // Short name is first 4 chars uppercased
      expect(unknownConfig.shortName).toBe('UNKN');
      // Letter is first char uppercased
      expect(unknownConfig.letter).toBe('U');
    });
  });

  describe('getStrategyColor', () => {
    it('returns correct hex color for known strategies', () => {
      expect(getStrategyColor('strat_orb_breakout')).toBe('#60a5fa');
      expect(getStrategyColor('strat_orb_scalp')).toBe('#c084fc');
      expect(getStrategyColor('strat_vwap_reclaim')).toBe('#2dd4bf');
      expect(getStrategyColor('strat_afternoon_momentum')).toBe('#fbbf24');
      expect(getStrategyColor('strat_red_to_green')).toBe('#fb923c');
      expect(getStrategyColor('strat_bull_flag')).toBe('#22d3ee');
      expect(getStrategyColor('strat_flat_top_breakout')).toBe('#a78bfa');
      expect(getStrategyColor('strat_dip_and_rip')).toBe('#fb7185');
      expect(getStrategyColor('strat_hod_break')).toBe('#34d399');
      expect(getStrategyColor('strat_gap_and_go')).toBe('#38bdf8');
      expect(getStrategyColor('strat_abcd')).toBe('#f472b6');
      expect(getStrategyColor('strat_premarket_high_break')).toBe('#a3e635');
    });

    it('returns grey fallback for unknown strategies', () => {
      expect(getStrategyColor('unknown_strategy')).toBe('#6b7280');
    });
  });

  describe('getStrategyBorderClass', () => {
    it('returns correct Tailwind class for known strategies', () => {
      expect(getStrategyBorderClass('strat_orb_breakout')).toBe('border-l-blue-400');
      expect(getStrategyBorderClass('strat_afternoon_momentum')).toBe('border-l-amber-400');
      expect(getStrategyBorderClass('strat_red_to_green')).toBe('border-l-orange-400');
      expect(getStrategyBorderClass('strat_bull_flag')).toBe('border-l-cyan-400');
      expect(getStrategyBorderClass('strat_flat_top_breakout')).toBe('border-l-violet-400');
      expect(getStrategyBorderClass('strat_dip_and_rip')).toBe('border-l-rose-400');
      expect(getStrategyBorderClass('strat_hod_break')).toBe('border-l-emerald-400');
      expect(getStrategyBorderClass('strat_gap_and_go')).toBe('border-l-sky-400');
      expect(getStrategyBorderClass('strat_abcd')).toBe('border-l-pink-400');
      expect(getStrategyBorderClass('strat_premarket_high_break')).toBe('border-l-lime-400');
    });

    it('returns grey fallback for unknown strategies', () => {
      expect(getStrategyBorderClass('unknown')).toBe('border-l-gray-400');
    });
  });

  describe('getStrategyBarClass', () => {
    it('returns correct Tailwind class for known strategies', () => {
      expect(getStrategyBarClass('strat_orb_breakout')).toBe('bg-blue-400');
      expect(getStrategyBarClass('strat_vwap_reclaim')).toBe('bg-teal-400');
      expect(getStrategyBarClass('strat_red_to_green')).toBe('bg-orange-400');
      expect(getStrategyBarClass('strat_bull_flag')).toBe('bg-cyan-400');
      expect(getStrategyBarClass('strat_flat_top_breakout')).toBe('bg-violet-400');
      expect(getStrategyBarClass('strat_dip_and_rip')).toBe('bg-rose-400');
      expect(getStrategyBarClass('strat_hod_break')).toBe('bg-emerald-400');
      expect(getStrategyBarClass('strat_gap_and_go')).toBe('bg-sky-400');
      expect(getStrategyBarClass('strat_abcd')).toBe('bg-pink-400');
      expect(getStrategyBarClass('strat_premarket_high_break')).toBe('bg-lime-400');
    });

    it('returns grey fallback for unknown strategies', () => {
      expect(getStrategyBarClass('unknown')).toBe('bg-gray-400');
    });
  });

  describe('getStrategyBadgeClass', () => {
    it('returns strategy-specific badge class for known strategies', () => {
      expect(getStrategyBadgeClass('strat_orb_breakout')).toBe('text-blue-400 bg-blue-400/15');
      expect(getStrategyBadgeClass('strat_micro_pullback')).toBe(
        'text-indigo-400 bg-indigo-400/15',
      );
      expect(getStrategyBadgeClass('strat_vwap_bounce')).toBe(
        'text-fuchsia-400 bg-fuchsia-400/15',
      );
      expect(getStrategyBadgeClass('strat_narrow_range_breakout')).toBe(
        'text-green-400 bg-green-400/15',
      );
    });

    it('returns amber-safe class when onAmber is true', () => {
      expect(getStrategyBadgeClass('strat_orb_breakout', true)).toBe(STRATEGY_AMBER_BADGE_CLASS);
      // Even unknown strategies get the amber-safe class
      expect(getStrategyBadgeClass('unknown_xyz', true)).toBe(STRATEGY_AMBER_BADGE_CLASS);
    });

    it('returns fallback class for unknown strategies (not onAmber)', () => {
      expect(getStrategyBadgeClass('unknown_xyz')).toBe('text-argus-text-dim bg-argus-surface-2');
    });
  });

  describe('helper accessors', () => {
    it('getStrategyLetter returns the configured letter', () => {
      expect(getStrategyLetter('strat_orb_breakout')).toBe('O');
      expect(getStrategyLetter('strat_micro_pullback')).toBe('M');
      expect(getStrategyLetter('strat_vwap_bounce')).toBe('B');
      expect(getStrategyLetter('strat_narrow_range_breakout')).toBe('N');
    });

    it('getStrategyShortName returns the configured short name', () => {
      expect(getStrategyShortName('strat_orb_breakout')).toBe('ORB');
      expect(getStrategyShortName('strat_afternoon_momentum')).toBe('PM');
      expect(getStrategyShortName('strat_micro_pullback')).toBe('MICRO');
    });

    it('getStrategyName returns the configured full name', () => {
      expect(getStrategyName('strat_orb_breakout')).toBe('ORB Breakout');
      expect(getStrategyName('strat_vwap_bounce')).toBe('VWAP Bounce');
      expect(getStrategyName('strat_narrow_range_breakout')).toBe('Narrow Range Breakout');
    });
  });

  describe('experiment-variant strategy IDs (IMPROMPTU-07, 2026-04-23)', () => {
    // Context: variants use `__` as a structural separator
    // (`strat_bull_flag__v2_strong_pole`). Before IMPROMPTU-07 these
    // fell through to the grey "unknown" fallback in getStrategyDisplay
    // and Tailwind accessors, so the Command Center rendered active
    // shadow variants as greyed-out "STRA" badges. The fix strips the
    // `__<variant>` suffix and inherits the base strategy's color +
    // shortName, while preserving the full variant ID in `badgeId`.
    it('getStrategyDisplay: variant inherits base color, name, short name', () => {
      const variant = getStrategyDisplay('strat_bull_flag__v2_strong_pole');
      // Inherits base (Bull Flag) color + display metadata.
      expect(variant.color).toBe('#22d3ee');
      expect(variant.shortName).toBe('FLAG');
      expect(variant.letter).toBe('F');
      expect(variant.name).toBe('Bull Flag');
      // But badgeId preserves the full variant id for test hooks /
      // tooltip disambiguation.
      expect(variant.badgeId).toBe('strat_bull_flag__v2_strong_pole');
    });

    it('getStrategyDisplay: dip_and_rip variants inherit rose color', () => {
      const v2 = getStrategyDisplay('strat_dip_and_rip__v2_tight_dip_quality');
      const v3 = getStrategyDisplay('strat_dip_and_rip__v3_strict_volume');
      expect(v2.color).toBe('#fb7185');
      expect(v3.color).toBe('#fb7185');
      expect(v2.shortName).toBe('DIP');
      expect(v3.shortName).toBe('DIP');
    });

    it('getStrategyBadgeClass: variant uses base strategy tint, not fallback', () => {
      const klass = getStrategyBadgeClass('strat_bull_flag__v2_strong_pole');
      expect(klass).toBe('text-cyan-400 bg-cyan-400/15');
      // Regression check: the old greyed-out fallback class is NOT used.
      expect(klass).not.toBe('text-argus-text-dim bg-argus-surface-2');
    });

    it('getStrategyBorderClass / getStrategyBarClass / getStrategyColor: all resolve variants to base', () => {
      expect(getStrategyBorderClass('strat_narrow_range_breakout__v2_deep_compression'))
        .toBe('border-l-green-400');
      expect(getStrategyBarClass('strat_gap_and_go__v3_direct_entry'))
        .toBe('bg-sky-400');
      expect(getStrategyColor('strat_hod_break__v2_volume_conviction'))
        .toBe('#34d399');
    });

    it('base strategy IDs remain unchanged (no false-positive stripping)', () => {
      // Without `__`, stripVariantSuffix is a no-op: base strategies
      // continue to render exactly as they did pre-fix.
      const orb = getStrategyDisplay('strat_orb_breakout');
      expect(orb.badgeId).toBe('strat_orb_breakout');
      expect(orb.color).toBe('#60a5fa');
      expect(getStrategyBadgeClass('strat_orb_breakout'))
        .toBe('text-blue-400 bg-blue-400/15');
    });

    it('truly unknown variant (unknown base) still falls through to grey', () => {
      // Defensive: a variant whose base isn't in STRATEGY_DISPLAY still
      // gets the grey fallback rather than crashing.
      const unknown = getStrategyDisplay('strat_totally_unknown__v2_foo');
      expect(unknown.color).toBe('#6b7280');
    });
  });
});
