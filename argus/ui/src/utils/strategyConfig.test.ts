/**
 * Tests for strategyConfig utility functions.
 *
 * Sprint 21.5.1, Session 3.
 */

import { describe, it, expect } from 'vitest';
import {
  getStrategyDisplay,
  getStrategyColor,
  getStrategyBorderClass,
  getStrategyBarClass,
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
    });

    it('returns correct short names for new strategies', () => {
      expect(getStrategyDisplay('strat_red_to_green').shortName).toBe('R2G');
      expect(getStrategyDisplay('strat_bull_flag').shortName).toBe('FLAG');
      expect(getStrategyDisplay('strat_flat_top_breakout').shortName).toBe('FLAT');
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
    });

    it('returns grey fallback for unknown strategies', () => {
      expect(getStrategyBarClass('unknown')).toBe('bg-gray-400');
    });
  });
});
