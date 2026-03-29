/**
 * Tests for StrategyHealthBands component.
 *
 * Sprint 28, Session 6c.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StrategyHealthBands } from './StrategyHealthBands';
import type { LearningReport, WeightRecommendation } from '../../api/learningApi';

function makeWeightRec(overrides?: Partial<WeightRecommendation>): WeightRecommendation {
  return {
    dimension: 'pattern_strength',
    current_weight: 0.30,
    recommended_weight: 0.35,
    delta: 0.05,
    correlation_trade_source: 0.42,
    correlation_counterfactual_source: 0.38,
    p_value: 0.023,
    sample_size: 150,
    confidence: 'MODERATE',
    regime_breakdown: {},
    source_divergence_flag: false,
    ...overrides,
  };
}

function makeReport(
  weightRecs: WeightRecommendation[] = [makeWeightRec()]
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
    weight_recommendations: weightRecs,
    threshold_recommendations: [],
    correlation_result: null,
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

  it('renders strategy bars with mock data', () => {
    const report = makeReport([
      makeWeightRec({ dimension: 'orb_breakout', sample_size: 80 }),
      makeWeightRec({ dimension: 'vwap_reclaim', sample_size: 45 }),
    ]);

    render(<StrategyHealthBands report={report} />);
    expect(screen.getByTestId('health-bands')).toBeInTheDocument();
    expect(screen.getByText('orb breakout')).toBeInTheDocument();
    expect(screen.getByText('vwap reclaim')).toBeInTheDocument();
    expect(screen.getByText('80 trades')).toBeInTheDocument();
    expect(screen.getByText('45 trades')).toBeInTheDocument();
  });

  it('renders empty state when report has no weight recommendations', () => {
    const report = makeReport([]);
    render(<StrategyHealthBands report={report} />);
    expect(screen.getByTestId('health-bands-empty')).toBeInTheDocument();
  });
});
