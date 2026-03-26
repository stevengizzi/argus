/**
 * Tests for VixRegimeCard component.
 *
 * Sprint 27.9, Session 4.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VixRegimeCard } from '../VixRegimeCard';
import type { VixCurrentResponse } from '../../../api/types';

// Mock useVixData hook
const mockUseVixData = vi.fn();

vi.mock('../../../hooks', () => ({
  useVixData: () => mockUseVixData(),
}));

const mockOkData: VixCurrentResponse = {
  status: 'ok',
  data_date: '2026-03-25',
  vix_close: 18.45,
  vol_of_vol_ratio: 1.12,
  vix_percentile: 42,
  term_structure_proxy: 0.95,
  realized_vol_20d: 15.3,
  variance_risk_premium: 3.15,
  regime: {
    vol_regime_phase: 'CALM',
    vol_regime_momentum: 'STABILIZING',
    term_structure_regime: 'CONTANGO',
    vrp_tier: 'COMPRESSED',
  },
  is_stale: false,
  last_updated: '2026-03-25T20:00:00Z',
  timestamp: '2026-03-25T20:00:00Z',
};

const mockStaleData: VixCurrentResponse = {
  ...mockOkData,
  status: 'stale',
  is_stale: true,
};

const mockUnavailableData: VixCurrentResponse = {
  status: 'unavailable',
  message: 'VIX data not available',
  timestamp: '2026-03-25T20:00:00Z',
};

describe('VixRegimeCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with data showing VIX close, regime, and VRP', () => {
    mockUseVixData.mockReturnValue({
      data: mockOkData,
      isLoading: false,
    });

    render(<VixRegimeCard />);

    expect(screen.getByTestId('vix-close')).toHaveTextContent('18.45');
    expect(screen.getByTestId('vrp-tier')).toHaveTextContent('VRP: COMPRESSED');
    expect(screen.getByTestId('vol-phase')).toHaveTextContent('CALM');
    expect(screen.getByText('VIX Regime')).toBeInTheDocument();
  });

  it('renders loading state with skeleton', () => {
    mockUseVixData.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    const { container } = render(<VixRegimeCard />);

    const pulsingElements = container.querySelectorAll('.animate-pulse');
    expect(pulsingElements.length).toBeGreaterThan(0);
    expect(screen.getByText('VIX Regime')).toBeInTheDocument();
  });

  it('renders stale state with stale badge visible', () => {
    mockUseVixData.mockReturnValue({
      data: mockStaleData,
      isLoading: false,
    });

    render(<VixRegimeCard />);

    expect(screen.getByTestId('stale-badge')).toHaveTextContent('Stale');
    expect(screen.getByTestId('vix-close')).toHaveTextContent('18.45');
  });

  it('returns null when VIX is disabled (no data)', () => {
    mockUseVixData.mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    const { container } = render(<VixRegimeCard />);

    expect(container.innerHTML).toBe('');
  });

  it('returns null when status is unavailable', () => {
    mockUseVixData.mockReturnValue({
      data: mockUnavailableData,
      isLoading: false,
    });

    const { container } = render(<VixRegimeCard />);

    expect(container.innerHTML).toBe('');
  });

  it('renders correct momentum arrow for each value', () => {
    // STABILIZING → ↑ green
    mockUseVixData.mockReturnValue({
      data: mockOkData,
      isLoading: false,
    });

    const { unmount } = render(<VixRegimeCard />);
    const arrow = screen.getByTestId('momentum-arrow');
    expect(arrow).toHaveTextContent('\u2191');
    expect(arrow.className).toContain('text-emerald-400');
    unmount();

    // DETERIORATING → ↓ red
    mockUseVixData.mockReturnValue({
      data: {
        ...mockOkData,
        regime: {
          ...mockOkData.regime,
          vol_regime_momentum: 'DETERIORATING',
        },
      },
      isLoading: false,
    });

    const { unmount: unmount2 } = render(<VixRegimeCard />);
    const arrow2 = screen.getByTestId('momentum-arrow');
    expect(arrow2).toHaveTextContent('\u2193');
    expect(arrow2.className).toContain('text-red-400');
    unmount2();

    // NEUTRAL → → gray
    mockUseVixData.mockReturnValue({
      data: {
        ...mockOkData,
        regime: {
          ...mockOkData.regime,
          vol_regime_momentum: 'NEUTRAL',
        },
      },
      isLoading: false,
    });

    render(<VixRegimeCard />);
    const arrow3 = screen.getByTestId('momentum-arrow');
    expect(arrow3).toHaveTextContent('\u2192');
    expect(arrow3.className).toContain('text-argus-text-dim');
  });
});
