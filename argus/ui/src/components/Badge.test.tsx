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
    expect(screen.getByText('MOM')).toBeInTheDocument();

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
    // Badge uses strategyId.toUpperCase().slice(0,4) as fallback on the original ID
    // 'strat_unknown_xyz'.toUpperCase().slice(0,4) = 'STRA'
    expect(screen.getByText('STRA')).toBeInTheDocument();
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
});
