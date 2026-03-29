/**
 * Tests for CorrelationMatrix component.
 *
 * Sprint 28, Session 6c.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CorrelationMatrix } from './CorrelationMatrix';
import type { CorrelationResult } from '../../api/learningApi';

function makeCorrelation(overrides?: Partial<CorrelationResult>): CorrelationResult {
  return {
    strategy_pairs: [['orb_breakout', 'vwap_reclaim']],
    correlation_matrix: { 'orb_breakout|vwap_reclaim': 0.35 },
    flagged_pairs: [],
    overlap_counts: { 'orb_breakout|vwap_reclaim': 15 },
    excluded_strategies: [],
    window_days: 30,
    ...overrides,
  };
}

describe('CorrelationMatrix', () => {
  it('renders empty state when correlationResult is null', () => {
    render(<CorrelationMatrix correlationResult={null} />);
    expect(screen.getByTestId('correlation-empty')).toBeInTheDocument();
    expect(
      screen.getByText('Correlation data will appear after the first analysis')
    ).toBeInTheDocument();
  });

  it('renders matrix with 2 strategies', () => {
    render(<CorrelationMatrix correlationResult={makeCorrelation()} />);
    expect(screen.getByTestId('correlation-matrix')).toBeInTheDocument();
    // Should have the SVG and color legend
    expect(screen.getByText('-1.0')).toBeInTheDocument();
    expect(screen.getByText('+1.0')).toBeInTheDocument();
  });

  it('shows flagged badge when flagged pairs exist', () => {
    const result = makeCorrelation({
      flagged_pairs: [['orb_breakout', 'vwap_reclaim']],
    });
    render(<CorrelationMatrix correlationResult={result} />);
    expect(screen.getByText('flagged')).toBeInTheDocument();
  });

  it('shows requires message when only 1 strategy', () => {
    const result: CorrelationResult = {
      strategy_pairs: [],
      correlation_matrix: {},
      flagged_pairs: [],
      overlap_counts: {},
      excluded_strategies: [],
      window_days: 30,
    };
    render(<CorrelationMatrix correlationResult={result} />);
    expect(screen.getByTestId('correlation-empty')).toBeInTheDocument();
  });
});
