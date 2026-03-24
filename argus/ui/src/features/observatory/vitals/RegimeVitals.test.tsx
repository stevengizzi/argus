/**
 * Tests for RegimeVitals component.
 *
 * Sprint 27.6, Session 10.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RegimeVitals } from './RegimeVitals';
import type { RegimeVectorSummary } from '../../../api/types';

function fullRegime(overrides: Partial<RegimeVectorSummary> = {}): RegimeVectorSummary {
  return {
    computed_at: '2026-03-24T14:30:00Z',
    trend_score: 0.6,
    trend_conviction: 0.8,
    volatility_level: 18.5,
    volatility_direction: 0.4,
    universe_breadth_score: 0.35,
    breadth_thrust: false,
    average_correlation: 0.42,
    correlation_regime: 'normal',
    sector_rotation_phase: 'risk_on',
    leading_sectors: ['Technology', 'Consumer Discretionary'],
    lagging_sectors: ['Utilities', 'Real Estate'],
    opening_drive_strength: 0.7,
    first_30min_range_ratio: 1.2,
    vwap_slope: 0.003,
    direction_change_count: 2,
    intraday_character: 'trending',
    primary_regime: 'BULLISH_TRENDING',
    regime_confidence: 0.75,
    ...overrides,
  };
}

describe('RegimeVitals', () => {
  it('renders all 6 dimension indicators with full data', () => {
    render(<RegimeVitals regime={fullRegime()} />);

    expect(screen.getByTestId('regime-vitals')).toBeInTheDocument();
    expect(screen.getByTestId('regime-trend')).toBeInTheDocument();
    expect(screen.getByTestId('regime-volatility')).toBeInTheDocument();
    expect(screen.getByTestId('regime-breadth')).toBeInTheDocument();
    expect(screen.getByTestId('regime-correlation')).toBeInTheDocument();
    expect(screen.getByTestId('regime-sector')).toBeInTheDocument();
    expect(screen.getByTestId('regime-intraday')).toBeInTheDocument();
    expect(screen.getByTestId('regime-confidence')).toBeInTheDocument();
  });

  it('renders nothing when regime_vector_summary is null', () => {
    const { container } = render(<RegimeVitals regime={null} />);

    expect(container.innerHTML).toBe('');
    expect(screen.queryByTestId('regime-vitals')).not.toBeInTheDocument();
  });

  it('shows "Pre-market" when intraday_character is null', () => {
    render(<RegimeVitals regime={fullRegime({ intraday_character: null })} />);

    const badge = screen.getByTestId('intraday-badge');
    expect(badge).toHaveTextContent('Pre-market');
  });

  it('shows "Warming up..." when breadth score is null', () => {
    render(
      <RegimeVitals
        regime={fullRegime({ universe_breadth_score: null, breadth_thrust: null })}
      />,
    );

    expect(screen.getByTestId('breadth-warming')).toHaveTextContent('Warming up...');
  });

  it('shows breadth thrust indicator when active', () => {
    render(<RegimeVitals regime={fullRegime({ breadth_thrust: true })} />);

    expect(screen.getByTestId('breadth-thrust')).toBeInTheDocument();
  });

  it('displays correct trend label for bullish/bearish/neutral', () => {
    const { rerender } = render(<RegimeVitals regime={fullRegime({ trend_score: 0.6 })} />);
    expect(screen.getByTestId('regime-trend')).toHaveTextContent('Bullish');

    rerender(<RegimeVitals regime={fullRegime({ trend_score: -0.5 })} />);
    expect(screen.getByTestId('regime-trend')).toHaveTextContent('Bearish');

    rerender(<RegimeVitals regime={fullRegime({ trend_score: 0.1 })} />);
    expect(screen.getByTestId('regime-trend')).toHaveTextContent('Neutral');
  });

  it('displays correlation regime badge', () => {
    render(<RegimeVitals regime={fullRegime({ correlation_regime: 'concentrated' })} />);

    expect(screen.getByTestId('regime-correlation')).toHaveTextContent('concentrated');
  });

  it('displays sector rotation phase', () => {
    render(<RegimeVitals regime={fullRegime({ sector_rotation_phase: 'risk_off' })} />);

    expect(screen.getByTestId('regime-sector')).toHaveTextContent('Risk Off');
  });

  it('displays confidence percentage', () => {
    render(<RegimeVitals regime={fullRegime({ regime_confidence: 0.82 })} />);

    expect(screen.getByTestId('regime-confidence')).toHaveTextContent('82%');
  });

  it('handles missing correlation regime gracefully', () => {
    render(<RegimeVitals regime={fullRegime({ correlation_regime: null })} />);

    expect(screen.getByTestId('regime-correlation')).toHaveTextContent('—');
  });

  it('displays volatility with direction arrow', () => {
    render(
      <RegimeVitals regime={fullRegime({ volatility_level: 22.3, volatility_direction: 0.5 })} />,
    );

    const volEl = screen.getByTestId('regime-volatility');
    expect(volEl).toHaveTextContent('22.3');
    expect(volEl).toHaveTextContent('\u2191');
  });
});
