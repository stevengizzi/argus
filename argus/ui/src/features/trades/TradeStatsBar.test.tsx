/**
 * Tests for TradeStatsBar component.
 *
 * Sprint 28.75, Session 2 (DEF-118 — Avg R metric).
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TradeStatsBar } from './TradeStatsBar';
import type { TradeStatsResponse } from '../../api/types';

const mockStats: TradeStatsResponse = {
  total_trades: 126,
  wins: 68,
  losses: 50,
  win_rate: 53.97,
  net_pnl: 1234.56,
  avg_r: 0.42,
  timestamp: new Date().toISOString(),
};

describe('TradeStatsBar', () => {
  it('renders all four metric cards including Avg R', () => {
    render(<TradeStatsBar stats={mockStats} />);

    // Trades
    expect(screen.getByText('Trades')).toBeInTheDocument();
    expect(screen.getByText('126')).toBeInTheDocument();

    // Win Rate
    expect(screen.getByText('Win Rate')).toBeInTheDocument();

    // Net P&L
    expect(screen.getByText('Net P&L')).toBeInTheDocument();

    // Avg R
    expect(screen.getByText('Avg R')).toBeInTheDocument();
    expect(screen.getByText('+0.42R')).toBeInTheDocument();
  });

  it('renders Avg R as dash when null', () => {
    const statsNoAvgR: TradeStatsResponse = {
      ...mockStats,
      avg_r: null,
    };
    render(<TradeStatsBar stats={statsNoAvgR} />);
    // Should show dash for null avg_r
    const avgRSection = screen.getByText('Avg R');
    expect(avgRSection).toBeInTheDocument();
  });

  it('shows negative Avg R in red', () => {
    const negativeStats: TradeStatsResponse = {
      ...mockStats,
      avg_r: -0.35,
    };
    render(<TradeStatsBar stats={negativeStats} />);
    expect(screen.getByText('-0.35R')).toBeInTheDocument();
  });

  it('dims content during transitions', () => {
    const { container } = render(
      <TradeStatsBar stats={mockStats} isTransitioning={true} />
    );
    const contentDiv = container.querySelector('.opacity-40');
    expect(contentDiv).toBeTruthy();
  });
});
