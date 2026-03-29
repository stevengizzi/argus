/**
 * Tests for StrategyHealthBands component.
 *
 * Sprint 28, Session S6cf-3.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StrategyHealthBands } from './StrategyHealthBands';
import type { LearningReport, StrategyMetricsSummary } from '../../api/learningApi';

function makeReport(
  metrics: Record<string, StrategyMetricsSummary> = {}
): LearningReport {
  return {
    report_id: 'r1',
    generated_at: '2026-03-28T12:00:00Z',
    analysis_window_start: '2026-03-01',
    analysis_window_end: '2026-03-28',
    data_quality: {
      trading_days_count: 20,
      total_trades: 200,
      total_counterfactual: 50,
      effective_sample_size: 180,
      known_data_gaps: [],
      earliest_date: '2026-03-01',
      latest_date: '2026-03-28',
    },
    weight_recommendations: [],
    threshold_recommendations: [],
    correlation_result: null,
    strategy_metrics: metrics,
    version: 1,
  };
}

describe('StrategyHealthBands', () => {
  it('renders empty state when report is null', () => {
    render(<StrategyHealthBands report={null} />);
    expect(screen.getByTestId('health-bands-empty')).toBeInTheDocument();
    expect(
      screen.getByText('Strategy health data will appear after the first analysis')
    ).toBeInTheDocument();
  });

  it('renders strategy bars with real metrics', () => {
    const report = makeReport({
      strat_orb_breakout: {
        strategy_id: 'strat_orb_breakout',
        sharpe: 1.82,
        win_rate: 0.55,
        expectancy: 0.42,
        trade_count: 80,
        source: 'trade',
      },
      strat_vwap_reclaim: {
        strategy_id: 'strat_vwap_reclaim',
        sharpe: 0.95,
        win_rate: 0.48,
        expectancy: 0.15,
        trade_count: 45,
        source: 'trade',
      },
    });

    render(<StrategyHealthBands report={report} />);
    expect(screen.getByTestId('health-bands')).toBeInTheDocument();
    expect(screen.getByText('Orb Breakout')).toBeInTheDocument();
    expect(screen.getByText('Vwap Reclaim')).toBeInTheDocument();
    expect(screen.getByText('80 trades')).toBeInTheDocument();
    expect(screen.getByText('45 trades')).toBeInTheDocument();
  });

  it('renders empty state when report has no strategy metrics', () => {
    const report = makeReport({});
    render(<StrategyHealthBands report={report} />);
    expect(screen.getByTestId('health-bands-empty')).toBeInTheDocument();
  });
});
