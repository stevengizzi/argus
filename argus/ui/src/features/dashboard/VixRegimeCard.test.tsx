/**
 * Tests for VixRegimeCard component.
 *
 * Sprint 28.75, Session 2 (DEF-120).
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VixRegimeCard } from './VixRegimeCard';

// Mock useVixData hook
vi.mock('../../hooks', () => ({
  useVixData: () => ({
    data: {
      status: 'ok',
      vix_close: 18.42,
      data_date: '2026-03-30',
      is_stale: false,
      regime: {
        vrp_tier: 'NORMAL',
        vol_regime_phase: 'CALM',
        vol_regime_momentum: 'STABILIZING',
      },
    },
    isLoading: false,
  }),
}));

describe('VixRegimeCard', () => {
  it('renders without h-full class on the card', () => {
    const { container } = render(<VixRegimeCard />);
    const card = container.firstChild as HTMLElement;
    expect(card).toBeTruthy();
    // Card should NOT have h-full (would cause viewport fill)
    expect(card.className).not.toContain('h-full');
  });

  it('renders VIX close value', () => {
    render(<VixRegimeCard />);
    expect(screen.getByTestId('vix-close')).toHaveTextContent('18.42');
  });

  it('renders VRP tier badge', () => {
    render(<VixRegimeCard />);
    expect(screen.getByTestId('vrp-tier')).toHaveTextContent('VRP: NORMAL');
  });

  it('renders momentum arrow', () => {
    render(<VixRegimeCard />);
    expect(screen.getByTestId('momentum-arrow')).toBeInTheDocument();
  });

  it('renders all elements in a single compact horizontal row', () => {
    const { container } = render(<VixRegimeCard />);
    // The compact row uses flex layout — all data elements share a parent flex container
    const flexRow = container.querySelector('.flex.items-center.gap-3');
    expect(flexRow).toBeTruthy();
    // All data elements should be inside the same flex row
    expect(flexRow?.querySelector('[data-testid="vix-close"]')).toBeTruthy();
    expect(flexRow?.querySelector('[data-testid="vrp-tier"]')).toBeTruthy();
    expect(flexRow?.querySelector('[data-testid="vol-phase"]')).toBeTruthy();
    expect(flexRow?.querySelector('[data-testid="momentum-arrow"]')).toBeTruthy();
  });
});
