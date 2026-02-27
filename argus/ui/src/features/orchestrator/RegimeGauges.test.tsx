/**
 * Tests for RegimeGauges component.
 *
 * Sprint 21b - Gauge-based regime indicator display.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RegimeGauges } from './RegimeGauges';

describe('RegimeGauges', () => {
  it('renders with indicator values showing bullish momentum', () => {
    const indicators = {
      spy_price: 450.0,
      spy_sma_20: 445.0,
      spy_sma_50: 440.0,
      spy_realized_vol_20d: 0.12,
      spy_roc_5d: 0.02, // Positive ROC = bullish
    };

    render(<RegimeGauges regimeIndicators={indicators} />);

    // Check for SPY price display
    expect(screen.getByText(/SPY \$450\.00/)).toBeInTheDocument();

    // Check for Bullish interpretation (momentum > 0.01)
    // Note: "Bullish" appears twice - as interpretation and as scale label
    // Use getAllByText to verify presence
    const bullishElements = screen.getAllByText('Bullish');
    expect(bullishElements.length).toBeGreaterThanOrEqual(1);
  });

  it('shows Normal volatility for mid-range vol', () => {
    const indicators = {
      spy_price: 450.0,
      spy_sma_20: 445.0,
      spy_sma_50: 440.0,
      spy_realized_vol_20d: 0.12, // Between 0.08 and 0.16 = Normal
      spy_roc_5d: 0.005,
    };

    render(<RegimeGauges regimeIndicators={indicators} />);

    // Check for Normal volatility label
    expect(screen.getByText('Normal')).toBeInTheDocument();

    // Check for annualized vol display
    expect(screen.getByText(/12\.0% ann\./)).toBeInTheDocument();
  });

  it('positions trend gauge marker at right side for strong bull', () => {
    const indicators = {
      spy_price: 460.0, // Above both SMAs
      spy_sma_20: 445.0,
      spy_sma_50: 440.0,
      spy_realized_vol_20d: 0.12,
      spy_roc_5d: 0.02,
    };

    render(<RegimeGauges regimeIndicators={indicators} />);

    // Trend score = +2 (above both), normalized = (2+2)/4 = 1.0
    // Marker should be at 100% (right side)
    const trendMarker = screen.getByTestId('gauge-marker-trend');
    expect(trendMarker).toHaveStyle({ left: 'calc(100% - 6px)' });
    expect(screen.getByText('Strong Bull')).toBeInTheDocument();
  });

  it('positions volatility gauge marker toward right for low volatility', () => {
    const indicators = {
      spy_price: 450.0,
      spy_sma_20: 445.0,
      spy_sma_50: 440.0,
      spy_realized_vol_20d: 0.05, // Very low vol = 5%
      spy_roc_5d: 0.0,
    };

    render(<RegimeGauges regimeIndicators={indicators} />);

    // Vol normalized: 1 - (0.05/0.5) = 0.9 (toward calm/right side)
    const volMarker = screen.getByTestId('gauge-marker-vol');
    expect(volMarker).toHaveStyle({ left: 'calc(90% - 6px)' });
    expect(screen.getByText('Low')).toBeInTheDocument();
  });

  it('positions momentum gauge marker at center for neutral momentum', () => {
    const indicators = {
      spy_price: 450.0,
      spy_sma_20: 450.0, // At SMA exactly
      spy_sma_50: 450.0,
      spy_realized_vol_20d: 0.12,
      spy_roc_5d: 0.0, // Zero ROC = neutral
    };

    render(<RegimeGauges regimeIndicators={indicators} />);

    // ROC 0% normalized: (0 + 0.05) / 0.1 = 0.5 (center)
    const momMarker = screen.getByTestId('gauge-marker-mom');
    expect(momMarker).toHaveStyle({ left: 'calc(50% - 6px)' });
    expect(screen.getByText('Neutral')).toBeInTheDocument();
  });

  it('shows unavailable message when no data provided', () => {
    render(<RegimeGauges regimeIndicators={{}} />);

    expect(screen.getByText('Regime data unavailable')).toBeInTheDocument();
  });

  it('shows scale labels for each gauge', () => {
    const indicators = {
      spy_price: 450.0,
      spy_sma_20: 445.0,
      spy_sma_50: 440.0,
      spy_realized_vol_20d: 0.12,
      spy_roc_5d: 0.02,
    };

    render(<RegimeGauges regimeIndicators={indicators} />);

    // Check scale labels
    expect(screen.getByText('Bear')).toBeInTheDocument();
    expect(screen.getByText('Bull')).toBeInTheDocument();
    expect(screen.getByText('Crisis')).toBeInTheDocument();
    expect(screen.getByText('Calm')).toBeInTheDocument();
    expect(screen.getByText('Bearish')).toBeInTheDocument();
    // Note: "Bullish" is both a scale label AND interpretation, so just one check
  });
});
