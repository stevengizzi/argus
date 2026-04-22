/**
 * Tests for Badge component strategy variants.
 *
 * Sprint 32.75 Session 1 — covers all 12 strategy IDs.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StrategyBadge, CompactStrategyBadge } from './Badge';

describe('StrategyBadge', () => {
  it('renders correct label for original 7 strategies', () => {
    const { rerender } = render(<StrategyBadge strategyId="strat_orb_breakout" />);
    expect(screen.getByText('ORB')).toBeInTheDocument();

    rerender(<StrategyBadge strategyId="strat_orb_scalp" />);
    expect(screen.getByText('SCALP')).toBeInTheDocument();

    rerender(<StrategyBadge strategyId="strat_vwap_reclaim" />);
    expect(screen.getByText('VWAP')).toBeInTheDocument();

    rerender(<StrategyBadge strategyId="strat_afternoon_momentum" />);
    // Consolidated source-of-truth (audit FIX-12 P1-F2-M01): Badge.tsx
    // now derives labels from strategyConfig.ts, which uses 'PM' for
    // afternoon_momentum. Pre-consolidation Badge.tsx hardcoded 'MOM'.
    expect(screen.getByText('PM')).toBeInTheDocument();

    rerender(<StrategyBadge strategyId="strat_red_to_green" />);
    expect(screen.getByText('R2G')).toBeInTheDocument();

    rerender(<StrategyBadge strategyId="strat_bull_flag" />);
    expect(screen.getByText('FLAG')).toBeInTheDocument();

    rerender(<StrategyBadge strategyId="strat_flat_top_breakout" />);
    expect(screen.getByText('FLAT')).toBeInTheDocument();
  });

  it('renders correct label for strat_dip_and_rip', () => {
    render(<StrategyBadge strategyId="strat_dip_and_rip" />);
    expect(screen.getByText('DIP')).toBeInTheDocument();
  });

  it('renders correct label for strat_hod_break', () => {
    render(<StrategyBadge strategyId="strat_hod_break" />);
    expect(screen.getByText('HOD')).toBeInTheDocument();
  });

  it('renders correct label for strat_gap_and_go', () => {
    render(<StrategyBadge strategyId="strat_gap_and_go" />);
    expect(screen.getByText('GAP')).toBeInTheDocument();
  });

  it('renders correct label for strat_abcd', () => {
    render(<StrategyBadge strategyId="strat_abcd" />);
    expect(screen.getByText('ABCD')).toBeInTheDocument();
  });

  it('renders correct label for strat_premarket_high_break', () => {
    render(<StrategyBadge strategyId="strat_premarket_high_break" />);
    expect(screen.getByText('PMH')).toBeInTheDocument();
  });

  it('strips strat_ prefix correctly for all 5 new strategies', () => {
    const cases: [string, string][] = [
      ['strat_dip_and_rip', 'DIP'],
      ['strat_hod_break', 'HOD'],
      ['strat_gap_and_go', 'GAP'],
      ['strat_abcd', 'ABCD'],
      ['strat_premarket_high_break', 'PMH'],
    ];
    for (const [id, expectedLabel] of cases) {
      const { unmount } = render(<StrategyBadge strategyId={id} />);
      expect(screen.getByText(expectedLabel)).toBeInTheDocument();
      unmount();
    }
  });

  it('applies correct color class for new strategies (not grey fallback)', () => {
    const { container } = render(<StrategyBadge strategyId="strat_dip_and_rip" />);
    const badge = container.querySelector('span');
    expect(badge?.className).toContain('rose-400');
    expect(badge?.className).not.toContain('argus-surface-2');
  });

  it('falls back gracefully for unknown strategy IDs', () => {
    render(<StrategyBadge strategyId="strat_unknown_xyz" />);
    // strategyConfig.getStrategyDisplay() uses strategyId.slice(0,4).toUpperCase()
    // on the original ID as the fallback shortName: 'strat_unknown_xyz'.slice(0,4) = 'stra'
    expect(screen.getByText('STRA')).toBeInTheDocument();
  });

  it('renders correct label for Sprint 31A strategies (audit FIX-12 P1-F2-C01)', () => {
    const cases: [string, string][] = [
      ['strat_micro_pullback', 'MICRO'],
      ['strat_vwap_bounce', 'VWB'],
      ['strat_narrow_range_breakout', 'NRB'],
    ];
    for (const [id, expectedLabel] of cases) {
      const { unmount } = render(<StrategyBadge strategyId={id} />);
      expect(screen.getByText(expectedLabel)).toBeInTheDocument();
      unmount();
    }
  });

  it('applies non-grey color class for Sprint 31A strategies (audit FIX-12 P1-F2-C01)', () => {
    const cases: [string, string][] = [
      ['strat_micro_pullback', 'indigo-400'],
      ['strat_vwap_bounce', 'fuchsia-400'],
      ['strat_narrow_range_breakout', 'green-400'],
    ];
    for (const [id, expectedColor] of cases) {
      const { container, unmount } = render(<StrategyBadge strategyId={id} />);
      const badge = container.querySelector('span');
      expect(badge?.className).toContain(expectedColor);
      expect(badge?.className).not.toContain('argus-surface-2');
      unmount();
    }
  });

  it('supports data-testid pass-through for test integration', () => {
    render(<StrategyBadge strategyId="strat_orb_breakout" data-testid="test-badge" />);
    expect(screen.getByTestId('test-badge')).toBeInTheDocument();
    expect(screen.getByTestId('test-badge')).toHaveTextContent('ORB');
  });
});

describe('CompactStrategyBadge', () => {
  it('renders correct letter for all 5 new strategies', () => {
    const cases: [string, string][] = [
      ['strat_dip_and_rip', 'D'],
      ['strat_hod_break', 'H'],
      ['strat_gap_and_go', 'G'],
      ['strat_abcd', 'X'],
      ['strat_premarket_high_break', 'P'],
    ];
    for (const [id, expectedLetter] of cases) {
      const { unmount } = render(<CompactStrategyBadge strategyId={id} />);
      expect(screen.getByText(expectedLetter)).toBeInTheDocument();
      unmount();
    }
  });

  it('renders correct letter for Sprint 31A strategies (audit FIX-12 P1-F2-C01)', () => {
    const cases: [string, string][] = [
      ['strat_micro_pullback', 'M'],
      ['strat_vwap_bounce', 'B'],
      ['strat_narrow_range_breakout', 'N'],
    ];
    for (const [id, expectedLetter] of cases) {
      const { unmount } = render(<CompactStrategyBadge strategyId={id} />);
      expect(screen.getByText(expectedLetter)).toBeInTheDocument();
      unmount();
    }
  });
});
