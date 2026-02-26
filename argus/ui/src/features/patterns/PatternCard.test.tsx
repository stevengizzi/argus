/**
 * Tests for PatternCard component.
 *
 * Sprint 21a, Session 3.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PatternCard } from './PatternCard';
import type { StrategyInfo } from '../../api/types';

// Mock strategy without performance data
const mockStrategyNoPerf: StrategyInfo = {
  strategy_id: 'orb_breakout',
  name: 'ORB Breakout',
  version: '1.0.0',
  is_active: true,
  pipeline_stage: 'paper_trading',
  allocated_capital: 10000,
  daily_pnl: 150,
  trade_count_today: 3,
  open_positions: 1,
  config_summary: {},
  time_window: '9:30 AM – 10:00 AM',
  family: 'orb_family',
  description_short: 'Opening range breakout strategy',
  performance_summary: null,
  backtest_summary: null,
};

// Mock strategy with performance data
const mockStrategyWithPerf: StrategyInfo = {
  ...mockStrategyNoPerf,
  strategy_id: 'vwap_reclaim',
  name: 'VWAP Reclaim',
  pipeline_stage: 'live_full',
  family: 'momentum',
  time_window: '10:00 AM – 2:00 PM',
  performance_summary: {
    trade_count: 125,
    win_rate: 0.62,
    net_pnl: 2450,
    avg_r: 1.3,
    profit_factor: 2.1,
  },
};

describe('PatternCard', () => {
  it('renders strategy name and badges', () => {
    const handleSelect = vi.fn();

    render(
      <PatternCard
        strategy={mockStrategyNoPerf}
        isSelected={false}
        onSelect={handleSelect}
      />
    );

    // Strategy name
    expect(screen.getByText('ORB Breakout')).toBeInTheDocument();

    // Pipeline stage badge
    expect(screen.getByText('Paper')).toBeInTheDocument();

    // Family label
    expect(screen.getByText('ORB Family')).toBeInTheDocument();

    // Time window
    expect(screen.getByText('9:30 AM – 10:00 AM')).toBeInTheDocument();
  });

  it('shows performance stats when available', () => {
    const handleSelect = vi.fn();

    render(
      <PatternCard
        strategy={mockStrategyWithPerf}
        isSelected={false}
        onSelect={handleSelect}
      />
    );

    // Trade count
    expect(screen.getByText('125')).toBeInTheDocument();

    // Win rate (62%)
    expect(screen.getByText('62%')).toBeInTheDocument();

    // P&L (+$2,450)
    expect(screen.getByText('+$2,450')).toBeInTheDocument();
  });

  it('shows dashes when performance data is not available', () => {
    const handleSelect = vi.fn();

    render(
      <PatternCard
        strategy={mockStrategyNoPerf}
        isSelected={false}
        onSelect={handleSelect}
      />
    );

    // Should show dashes for missing performance data
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBe(3); // Trades, Win %, P&L
  });

  it('click calls onSelect with correct ID', () => {
    const handleSelect = vi.fn();

    render(
      <PatternCard
        strategy={mockStrategyWithPerf}
        isSelected={false}
        onSelect={handleSelect}
      />
    );

    // Click on the card
    const cardContent = screen.getByText('VWAP Reclaim').closest('div');
    if (cardContent) {
      fireEvent.click(cardContent);
    }

    expect(handleSelect).toHaveBeenCalledWith('vwap_reclaim');
  });
});
