/**
 * Tests for IncubatorPipeline component.
 *
 * Sprint 21a, Session 3.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { IncubatorPipeline, PIPELINE_STAGES } from './IncubatorPipeline';
import type { StrategyInfo } from '../../api/types';

// Mock strategy data
const mockStrategies: StrategyInfo[] = [
  {
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
  },
  {
    strategy_id: 'vwap_reclaim',
    name: 'VWAP Reclaim',
    version: '1.0.0',
    is_active: true,
    pipeline_stage: 'paper_trading',
    allocated_capital: 10000,
    daily_pnl: 75,
    trade_count_today: 2,
    open_positions: 0,
    config_summary: {},
    time_window: '10:00 AM – 2:00 PM',
    family: 'momentum',
    description_short: 'VWAP reclaim strategy',
    performance_summary: null,
    backtest_summary: null,
  },
  {
    strategy_id: 'afternoon_momentum',
    name: 'Afternoon Momentum',
    version: '1.0.0',
    is_active: false,
    pipeline_stage: 'validation',
    allocated_capital: 0,
    daily_pnl: 0,
    trade_count_today: 0,
    open_positions: 0,
    config_summary: {},
    time_window: '1:00 PM – 3:55 PM',
    family: 'momentum',
    description_short: 'Afternoon breakout strategy',
    performance_summary: null,
    backtest_summary: null,
  },
];

describe('IncubatorPipeline', () => {
  it('renders all 10 stage labels', () => {
    const handleClick = vi.fn();

    render(
      <IncubatorPipeline
        strategies={[]}
        activeStageFilter={null}
        onStageClick={handleClick}
      />
    );

    // Check that all stages are rendered
    PIPELINE_STAGES.forEach((stage) => {
      expect(screen.getByText(new RegExp(stage.label))).toBeInTheDocument();
    });
  });

  it('shows correct count for stages with strategies', () => {
    const handleClick = vi.fn();

    render(
      <IncubatorPipeline
        strategies={mockStrategies}
        activeStageFilter={null}
        onStageClick={handleClick}
      />
    );

    // paper_trading has 2 strategies
    const paperButton = screen.getByRole('button', { name: /Paper.*\(2\)/ });
    expect(paperButton).toBeInTheDocument();

    // validation has 1 strategy
    const validateButton = screen.getByRole('button', { name: /Validate.*\(1\)/ });
    expect(validateButton).toBeInTheDocument();
  });

  it('click toggles filter (calls onStageClick)', () => {
    const handleClick = vi.fn();

    const { rerender } = render(
      <IncubatorPipeline
        strategies={mockStrategies}
        activeStageFilter={null}
        onStageClick={handleClick}
      />
    );

    // Click on paper_trading stage
    const paperButton = screen.getByRole('button', { name: /Paper/ });
    fireEvent.click(paperButton);

    // Should call with 'paper_trading'
    expect(handleClick).toHaveBeenCalledWith('paper_trading');

    // Re-render with paper_trading active
    handleClick.mockClear();
    rerender(
      <IncubatorPipeline
        strategies={mockStrategies}
        activeStageFilter="paper_trading"
        onStageClick={handleClick}
      />
    );

    // Click on the same stage again should clear filter (call with null)
    const paperButtonActive = screen.getByRole('button', { name: /Paper/ });
    fireEvent.click(paperButtonActive);

    expect(handleClick).toHaveBeenCalledWith(null);
  });
});
