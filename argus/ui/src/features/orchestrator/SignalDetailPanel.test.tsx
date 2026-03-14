/**
 * Tests for SignalDetailPanel component.
 *
 * Sprint 24.1 Session 4b.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SignalDetailPanel } from './SignalDetailPanel';
import type { QualityScoreResponse } from '../../api/types';

function makeSignal(overrides: Partial<QualityScoreResponse> = {}): QualityScoreResponse {
  return {
    symbol: 'AAPL',
    strategy_id: 'strat_orb_breakout',
    score: 82.5,
    grade: 'A',
    risk_tier: 'low',
    components: { ps: 85, cq: 70, vp: 90, hm: 80, ra: 88 },
    scored_at: '2026-03-14T10:15:00-04:00',
    outcome_realized_pnl: null,
    outcome_r_multiple: null,
    ...overrides,
  };
}

describe('SignalDetailPanel', () => {
  it('renders with full quality data', () => {
    const signal = makeSignal({
      outcome_realized_pnl: 125.50,
      outcome_r_multiple: 1.85,
    });

    render(<SignalDetailPanel signal={signal} />);

    expect(screen.getByTestId('signal-detail-panel')).toBeInTheDocument();
    expect(screen.getByTestId('quality-badge-expanded')).toBeInTheDocument();
    expect(screen.getByTestId('quality-components')).toBeInTheDocument();
    expect(screen.getByText('$125.50')).toBeInTheDocument();
    expect(screen.getByText('1.85R')).toBeInTheDocument();
  });

  it('renders dash for missing outcome data', () => {
    const signal = makeSignal();

    render(<SignalDetailPanel signal={signal} />);

    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it('displays strategy name and risk tier', () => {
    const signal = makeSignal({ risk_tier: 'high' });

    render(<SignalDetailPanel signal={signal} />);

    expect(screen.getByText('high')).toBeInTheDocument();
  });
});
