/**
 * Tests for BacktestTab component.
 *
 * Sprint 21a, Session 4.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BacktestTab } from './BacktestTab';
import type { StrategyInfo, BacktestSummary } from '../../../api/types';

// Base mock strategy
const createMockStrategy = (backtest: BacktestSummary | null): StrategyInfo => ({
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
  backtest_summary: backtest,
});

describe('BacktestTab', () => {
  it('renders correct status badge for walk_forward_complete', () => {
    const strategy = createMockStrategy({
      status: 'walk_forward_complete',
      wfe_pnl: 5000,
      oos_sharpe: 1.8,
      total_trades: 250,
      data_months: 12,
      last_run: '2026-02-20T10:00:00Z',
    });

    render(<BacktestTab strategy={strategy} />);

    expect(screen.getByText('Walk-Forward Complete')).toBeInTheDocument();
  });

  it('renders correct status badge for sweep_complete', () => {
    const strategy = createMockStrategy({
      status: 'sweep_complete',
      wfe_pnl: null,
      oos_sharpe: null,
      total_trades: 150,
      data_months: 8,
      last_run: '2026-02-15T10:00:00Z',
    });

    render(<BacktestTab strategy={strategy} />);

    expect(screen.getByText('Parameter Sweep Complete')).toBeInTheDocument();
  });

  it('renders correct status badge for not_validated', () => {
    const strategy = createMockStrategy({
      status: 'not_validated',
      wfe_pnl: null,
      oos_sharpe: null,
      total_trades: null,
      data_months: null,
      last_run: null,
    });

    render(<BacktestTab strategy={strategy} />);

    expect(screen.getByText('Not Yet Validated')).toBeInTheDocument();
  });

  it('shows summary metrics when available', () => {
    const strategy = createMockStrategy({
      status: 'walk_forward_complete',
      wfe_pnl: 5000,
      oos_sharpe: 1.85,
      total_trades: 250,
      data_months: 12,
      last_run: '2026-02-20T10:00:00Z',
    });

    render(<BacktestTab strategy={strategy} />);

    // WFE P&L
    expect(screen.getByText('WFE (P&L)')).toBeInTheDocument();
    expect(screen.getByText('$5,000')).toBeInTheDocument();

    // OOS Sharpe
    expect(screen.getByText('OOS Sharpe')).toBeInTheDocument();
    expect(screen.getByText('1.85')).toBeInTheDocument();

    // Total Trades
    expect(screen.getByText('Total Trades')).toBeInTheDocument();
    expect(screen.getByText('250')).toBeInTheDocument();

    // Data Coverage
    expect(screen.getByText('Data Coverage')).toBeInTheDocument();
    expect(screen.getByText('12 months')).toBeInTheDocument();

    // Data validation note
    expect(
      screen.getByText(/All pre-Databento backtests require re-validation/)
    ).toBeInTheDocument();
  });
});
