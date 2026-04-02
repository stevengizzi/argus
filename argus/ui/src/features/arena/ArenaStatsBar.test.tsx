/**
 * Tests for ArenaStatsBar component.
 *
 * Sprint 32.75, Session 12f.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ArenaStatsBar } from './ArenaStatsBar';

describe('ArenaStatsBar', () => {
  it('renders all five stat labels', () => {
    render(<ArenaStatsBar />);
    expect(screen.getByTestId('arena-stats-bar')).toBeInTheDocument();
    expect(screen.getByTestId('stat-position-count')).toBeInTheDocument();
    expect(screen.getByTestId('stat-total-pnl')).toBeInTheDocument();
    expect(screen.getByTestId('stat-net-r')).toBeInTheDocument();
    expect(screen.getByTestId('stat-entries-5m')).toBeInTheDocument();
    expect(screen.getByTestId('stat-exits-5m')).toBeInTheDocument();
  });

  it('netR > 0 renders with profit color and + sign', () => {
    render(<ArenaStatsBar netR={2.5} />);
    const el = screen.getByTestId('stat-net-r');
    expect(el.className).toContain('text-argus-profit');
    expect(el.textContent).toContain('+');
  });

  it('netR < 0 renders with loss color and no + sign', () => {
    render(<ArenaStatsBar netR={-1.5} />);
    const el = screen.getByTestId('stat-net-r');
    expect(el.className).toContain('text-argus-loss');
    expect(el.textContent).not.toContain('+');
  });

  it('netR === 0 renders with dim color and no sign prefix', () => {
    render(<ArenaStatsBar netR={0} />);
    const el = screen.getByTestId('stat-net-r');
    expect(el.className).toContain('text-argus-text-dim');
    expect(el.textContent).not.toContain('+');
    expect(el.textContent).not.toContain('-');
  });
});
