/**
 * Tests for LearningDashboardCard component.
 *
 * Sprint 28, Session 6c.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LearningDashboardCard } from './LearningDashboardCard';

// Mock hooks
const mockUseLearningReport = vi.fn();
const mockUseConfigProposals = vi.fn();

vi.mock('../../hooks/useLearningReport', () => ({
  useLearningReport: (...args: unknown[]) => mockUseLearningReport(...args),
}));

vi.mock('../../hooks/useConfigProposals', () => ({
  useConfigProposals: (...args: unknown[]) => mockUseConfigProposals(...args),
}));

function renderCard(enabled = true) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LearningDashboardCard enabled={enabled} />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('LearningDashboardCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseLearningReport.mockReturnValue({
      report: null,
      isLoading: false,
      isError: false,
      error: null,
    });
    mockUseConfigProposals.mockReturnValue({
      data: { proposals: [], count: 0, timestamp: '' },
    });
  });

  it('returns null when disabled', () => {
    const { container } = renderCard(false);
    expect(container.innerHTML).toBe('');
  });

  it('renders card with pending count badge', () => {
    mockUseLearningReport.mockReturnValue({
      report: {
        report_id: 'r1',
        generated_at: new Date().toISOString(),
        data_quality: {
          trading_days_count: 25,
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
        version: 1,
      },
      isLoading: false,
    });
    mockUseConfigProposals.mockReturnValue({
      data: {
        proposals: [
          { proposal_id: 'p1', status: 'PENDING' },
          { proposal_id: 'p2', status: 'PENDING' },
          { proposal_id: 'p3', status: 'PENDING' },
        ],
        count: 3,
        timestamp: '',
      },
    });

    renderCard();
    expect(screen.getByTestId('learning-dashboard-card')).toBeInTheDocument();
    expect(screen.getByTestId('pending-count-badge')).toHaveTextContent('3');
    expect(screen.getByText('3 recommendations')).toBeInTheDocument();
    expect(screen.getByText('Sufficient')).toBeInTheDocument();
  });

  it('renders View Insights link', () => {
    mockUseLearningReport.mockReturnValue({
      report: {
        report_id: 'r1',
        generated_at: new Date().toISOString(),
        data_quality: {
          trading_days_count: 3,
          total_trades: 10,
          total_counterfactual: 2,
          effective_sample_size: 10,
          known_data_gaps: [],
          earliest_date: null,
          latest_date: null,
        },
        weight_recommendations: [],
        threshold_recommendations: [],
        correlation_result: null,
        version: 1,
      },
      isLoading: false,
    });

    renderCard();
    expect(screen.getByTestId('view-insights-link')).toBeInTheDocument();
    // Sparse data quality for low sample size
    expect(screen.getByText('Sparse')).toBeInTheDocument();
  });
});
