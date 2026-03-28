/**
 * Tests for WeightRecommendationCard component.
 *
 * Sprint 28, Session 6a.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WeightRecommendationCard } from './WeightRecommendationCard';
import type { WeightRecommendation } from '../../api/learningApi';

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
    regime_breakdown: { bullish: 0.5, bearish: 0.3 },
    source_divergence_flag: false,
    ...overrides,
  };
}

describe('WeightRecommendationCard', () => {
  const noop = vi.fn();

  it('renders dimension name, weights, and delta', () => {
    render(
      <WeightRecommendationCard
        recommendation={makeWeightRec()}
        proposalId="p1"
        status="PENDING"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.getByText('pattern_strength')).toBeInTheDocument();
    expect(screen.getByText('0.30')).toBeInTheDocument();
    expect(screen.getByText('0.35')).toBeInTheDocument();
    expect(screen.getByText('(+0.05)')).toBeInTheDocument();
  });

  it('renders confidence badge with MODERATE color', () => {
    const { container } = render(
      <WeightRecommendationCard
        recommendation={makeWeightRec()}
        proposalId="p1"
        status="PENDING"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    const badge = container.querySelector('[data-testid="confidence-badge"]');
    expect(badge?.textContent).toBe('Moderate');
    expect(badge?.className).toContain('text-amber-400');
  });

  it('renders correlation values, p-value, and sample size', () => {
    render(
      <WeightRecommendationCard
        recommendation={makeWeightRec()}
        proposalId="p1"
        status="PENDING"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.getByText('0.420')).toBeInTheDocument();
    expect(screen.getByText('0.380')).toBeInTheDocument();
    expect(screen.getByText('0.0230')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
  });

  it('shows source divergence warning when flagged', () => {
    render(
      <WeightRecommendationCard
        recommendation={makeWeightRec({ source_divergence_flag: true })}
        proposalId="p1"
        status="PENDING"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.getByTestId('divergence-warning')).toBeInTheDocument();
  });

  it('does not show divergence warning when not flagged', () => {
    render(
      <WeightRecommendationCard
        recommendation={makeWeightRec()}
        proposalId="p1"
        status="PENDING"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.queryByTestId('divergence-warning')).toBeNull();
  });

  it('shows approve and dismiss buttons for PENDING status', () => {
    render(
      <WeightRecommendationCard
        recommendation={makeWeightRec()}
        proposalId="p1"
        status="PENDING"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.getByTestId('approve-button')).toBeInTheDocument();
    expect(screen.getByTestId('dismiss-button')).toBeInTheDocument();
  });

  it('approve click shows notes textarea, confirm calls onApprove', () => {
    const onApprove = vi.fn();
    render(
      <WeightRecommendationCard
        recommendation={makeWeightRec()}
        proposalId="p1"
        status="PENDING"
        humanNotes={null}
        onApprove={onApprove}
        onDismiss={noop}
      />
    );

    // First click expands notes
    fireEvent.click(screen.getByTestId('approve-button'));
    expect(screen.getByTestId('notes-input')).toBeInTheDocument();
    expect(screen.getByTestId('approve-button').textContent).toBe('Confirm Approve');

    // Second click confirms without notes
    fireEvent.click(screen.getByTestId('approve-button'));
    expect(onApprove).toHaveBeenCalledWith('p1', undefined);
  });

  it('approve with notes passes notes to onApprove', () => {
    const onApprove = vi.fn();
    render(
      <WeightRecommendationCard
        recommendation={makeWeightRec()}
        proposalId="p1"
        status="PENDING"
        humanNotes={null}
        onApprove={onApprove}
        onDismiss={noop}
      />
    );

    fireEvent.click(screen.getByTestId('approve-button'));
    fireEvent.change(screen.getByTestId('notes-input'), {
      target: { value: 'Looks good' },
    });
    fireEvent.click(screen.getByTestId('approve-button'));
    expect(onApprove).toHaveBeenCalledWith('p1', 'Looks good');
  });

  it('renders approved state with green checkmark', () => {
    render(
      <WeightRecommendationCard
        recommendation={makeWeightRec()}
        proposalId="p1"
        status="APPROVED"
        humanNotes="Approved by operator"
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.getByTestId('approved-state')).toBeInTheDocument();
    expect(screen.queryByTestId('approve-button')).toBeNull();
    expect(screen.getByText('Approved by operator')).toBeInTheDocument();
  });

  it('renders dismissed state greyed out', () => {
    const { container } = render(
      <WeightRecommendationCard
        recommendation={makeWeightRec()}
        proposalId="p1"
        status="DISMISSED"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.getByTestId('dismissed-state')).toBeInTheDocument();
    const card = container.querySelector('[data-testid="weight-recommendation-card"]');
    expect(card?.className).toContain('opacity-50');
  });

  it('renders SUPERSEDED state with strikethrough and label', () => {
    render(
      <WeightRecommendationCard
        recommendation={makeWeightRec()}
        proposalId="p1"
        status="SUPERSEDED"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.getByTestId('superseded-label')).toBeInTheDocument();
    expect(screen.getByText('pattern_strength').className).toContain('line-through');
    // No action buttons for superseded
    expect(screen.queryByTestId('approve-button')).toBeNull();
    expect(screen.queryByTestId('dismiss-button')).toBeNull();
  });

  it('renders APPLIED status with revert button', () => {
    const onRevert = vi.fn();
    render(
      <WeightRecommendationCard
        recommendation={makeWeightRec()}
        proposalId="p1"
        status="APPLIED"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
        onRevert={onRevert}
      />
    );

    const revertBtn = screen.getByTestId('revert-button');
    expect(revertBtn).toBeInTheDocument();
    fireEvent.click(revertBtn);
    expect(onRevert).toHaveBeenCalledWith('p1');
  });
});
