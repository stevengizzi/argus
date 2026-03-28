/**
 * Tests for ThresholdRecommendationCard component.
 *
 * Sprint 28, Session 6a.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThresholdRecommendationCard } from './ThresholdRecommendationCard';
import type { ThresholdRecommendation } from '../../api/learningApi';

function makeThresholdRec(
  overrides?: Partial<ThresholdRecommendation>
): ThresholdRecommendation {
  return {
    grade: 'B+',
    current_threshold: 65.0,
    recommended_direction: 'lower',
    missed_opportunity_rate: 0.23,
    correct_rejection_rate: 0.81,
    sample_size: 89,
    confidence: 'INSUFFICIENT_DATA',
    ...overrides,
  };
}

describe('ThresholdRecommendationCard', () => {
  const noop = vi.fn();

  it('renders grade name, threshold, and direction', () => {
    render(
      <ThresholdRecommendationCard
        recommendation={makeThresholdRec()}
        proposalId="p2"
        status="PENDING"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.getByText('Grade B+')).toBeInTheDocument();
    expect(screen.getByText(/65\.0/)).toBeInTheDocument();
    expect(screen.getByText('lower')).toBeInTheDocument();
    expect(screen.getByTestId('direction-arrow').textContent).toBe('\u2193');
  });

  it('renders raise direction with up arrow', () => {
    render(
      <ThresholdRecommendationCard
        recommendation={makeThresholdRec({ recommended_direction: 'raise' })}
        proposalId="p2"
        status="PENDING"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.getByTestId('direction-arrow').textContent).toBe('\u2191');
    expect(screen.getByText('raise')).toBeInTheDocument();
  });

  it('renders INSUFFICIENT_DATA confidence badge', () => {
    const { container } = render(
      <ThresholdRecommendationCard
        recommendation={makeThresholdRec()}
        proposalId="p2"
        status="PENDING"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    const badge = container.querySelector('[data-testid="confidence-badge"]');
    expect(badge?.textContent).toBe('Insufficient Data');
    expect(badge?.className).toContain('text-gray-400');
  });

  it('renders missed opportunity and correct rejection rates', () => {
    render(
      <ThresholdRecommendationCard
        recommendation={makeThresholdRec()}
        proposalId="p2"
        status="PENDING"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.getByText('23.0%')).toBeInTheDocument();
    expect(screen.getByText('81.0%')).toBeInTheDocument();
    expect(screen.getByText('89')).toBeInTheDocument();
  });

  it('dismiss interaction works', () => {
    const onDismiss = vi.fn();
    render(
      <ThresholdRecommendationCard
        recommendation={makeThresholdRec()}
        proposalId="p2"
        status="PENDING"
        humanNotes={null}
        onApprove={noop}
        onDismiss={onDismiss}
      />
    );

    fireEvent.click(screen.getByTestId('dismiss-button'));
    expect(screen.getByTestId('notes-input')).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('notes-input'), {
      target: { value: 'Not enough data' },
    });
    fireEvent.click(screen.getByTestId('dismiss-button'));
    expect(onDismiss).toHaveBeenCalledWith('p2', 'Not enough data');
  });

  it('SUPERSEDED state shows strikethrough and no action buttons', () => {
    render(
      <ThresholdRecommendationCard
        recommendation={makeThresholdRec()}
        proposalId="p2"
        status="SUPERSEDED"
        humanNotes={null}
        onApprove={noop}
        onDismiss={noop}
      />
    );

    expect(screen.getByTestId('superseded-label')).toBeInTheDocument();
    expect(screen.getByText('Grade B+').className).toContain('line-through');
    expect(screen.queryByTestId('approve-button')).toBeNull();
    expect(screen.queryByTestId('dismiss-button')).toBeNull();
  });
});
