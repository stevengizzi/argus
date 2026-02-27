/**
 * Tests for RegimeInputBreakdown component.
 *
 * Sprint 21b, Session 8.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RegimeInputBreakdown } from './RegimeInputBreakdown';

describe('RegimeInputBreakdown', () => {
  it('renders with indicator values showing bullish momentum', () => {
    const indicators = {
      spy_price: 450.0,
      spy_sma_20: 445.0,
      spy_sma_50: 440.0,
      spy_realized_vol_20d: 0.12,
      spy_roc_5d: 0.02, // Positive ROC = bullish
    };

    render(<RegimeInputBreakdown regimeIndicators={indicators} />);

    // Check for SPY price display
    expect(screen.getByText(/\$450\.00/)).toBeInTheDocument();

    // Check for Bullish label (momentum > 0.01)
    expect(screen.getByText('Bullish')).toBeInTheDocument();
  });

  it('shows Normal volatility for mid-range vol', () => {
    const indicators = {
      spy_price: 450.0,
      spy_sma_20: 445.0,
      spy_sma_50: 440.0,
      spy_realized_vol_20d: 0.12, // Between 0.08 and 0.16 = Normal
      spy_roc_5d: 0.005,
    };

    render(<RegimeInputBreakdown regimeIndicators={indicators} />);

    // Check for Normal volatility label
    expect(screen.getByText('Normal')).toBeInTheDocument();

    // Check for annualized vol display
    expect(screen.getByText(/12\.0% ann\./)).toBeInTheDocument();
  });
});
