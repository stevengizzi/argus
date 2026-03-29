/**
 * Tests for LearningInsightsPanel component.
 *
 * Sprint 28, Session 6b.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LearningInsightsPanel } from './LearningInsightsPanel';

// Mock the hooks
vi.mock('../../hooks/useLearningReport', () => ({
  useLearningReport: vi.fn(),
  useLearningReports: vi.fn(),
  useTriggerAnalysis: vi.fn(),
}));

vi.mock('../../hooks/useConfigProposals', () => ({
  useConfigProposals: vi.fn(),
  useApproveProposal: vi.fn(),
  useDismissProposal: vi.fn(),
  useRevertProposal: vi.fn(),
}));

import { useLearningReport, useLearningReports, useTriggerAnalysis } from '../../hooks/useLearningReport';
import { useConfigProposals, useApproveProposal, useDismissProposal, useRevertProposal } from '../../hooks/useConfigProposals';

const mockReport = {
  report_id: 'rpt-001',
  generated_at: '2026-03-28T14:00:00Z',
  analysis_window_start: '2026-03-01',
  analysis_window_end: '2026-03-28',
  data_quality: {
    trading_days_count: 20,
    total_trades: 180,
    total_counterfactual: 45,
    effective_sample_size: 150,
    known_data_gaps: [],
    earliest_date: '2026-03-01',
    latest_date: '2026-03-28',
  },
  weight_recommendations: [
    {
      dimension: 'pattern_strength',
      current_weight: 0.30,
      recommended_weight: 0.35,
      delta: 0.05,
      correlation_trade_source: 0.42,
      correlation_counterfactual_source: 0.38,
      p_value: 0.023,
      sample_size: 150,
      confidence: 'MODERATE' as const,
      regime_breakdown: {},
      source_divergence_flag: false,
    },
  ],
  threshold_recommendations: [
    {
      grade: 'B',
      current_threshold: 65.0,
      recommended_direction: 'raise' as const,
      missed_opportunity_rate: 0.12,
      correct_rejection_rate: 0.78,
      sample_size: 80,
      confidence: 'HIGH' as const,
    },
  ],
  correlation_result: null,
  strategy_metrics: {},
  version: 1,
};

const mockProposals = {
  proposals: [
    {
      proposal_id: 'prop-1',
      report_id: 'rpt-001',
      field_path: 'quality_engine.weights.pattern_strength',
      current_value: 0.30,
      proposed_value: 0.35,
      rationale: 'Higher correlation',
      status: 'PENDING' as const,
      created_at: '2026-03-28T14:00:00Z',
      updated_at: '2026-03-28T14:00:00Z',
      human_notes: null,
    },
    {
      proposal_id: 'prop-2',
      report_id: 'rpt-001',
      field_path: 'quality_engine.thresholds.B',
      current_value: 65.0,
      proposed_value: 70.0,
      rationale: 'Raise grade B',
      status: 'PENDING' as const,
      created_at: '2026-03-28T14:00:00Z',
      updated_at: '2026-03-28T14:00:00Z',
      human_notes: null,
    },
  ],
  count: 2,
  timestamp: '2026-03-28T14:00:00Z',
};

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

function setupDefaultMocks() {
  const mutateFn = vi.fn();

  vi.mocked(useLearningReport).mockReturnValue({
    report: mockReport,
    isLoading: false,
    isError: false,
    error: null,
  });

  vi.mocked(useLearningReports).mockReturnValue({
    data: { reports: [{ report_id: 'rpt-001', generated_at: '2026-03-28T14:00:00Z', analysis_window_start: '2026-03-01', analysis_window_end: '2026-03-28', weight_recommendations: 1, threshold_recommendations: 1, version: 1 }], count: 1, timestamp: '2026-03-28T14:00:00Z' },
    isLoading: false,
    isError: false,
    error: null,
  } as ReturnType<typeof useLearningReports>);

  vi.mocked(useTriggerAnalysis).mockReturnValue({
    mutate: mutateFn,
    isPending: false,
  } as unknown as ReturnType<typeof useTriggerAnalysis>);

  vi.mocked(useConfigProposals).mockReturnValue({
    data: mockProposals,
    isLoading: false,
    isError: false,
    error: null,
  } as ReturnType<typeof useConfigProposals>);

  vi.mocked(useApproveProposal).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useApproveProposal>);

  vi.mocked(useDismissProposal).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useDismissProposal>);

  vi.mocked(useRevertProposal).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useRevertProposal>);

  return { mutateFn };
}

describe('LearningInsightsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders report with weight and threshold recommendation cards', () => {
    setupDefaultMocks();
    renderWithProviders(<LearningInsightsPanel />);

    expect(screen.getByTestId('learning-insights-panel')).toBeInTheDocument();
    // Weight recommendation
    expect(screen.getByText('pattern_strength')).toBeInTheDocument();
    // Threshold recommendation
    expect(screen.getByText('Grade B')).toBeInTheDocument();
    // Data quality
    expect(screen.getByText('20')).toBeInTheDocument(); // trading days
    expect(screen.getByText('180')).toBeInTheDocument(); // total trades
  });

  it('renders empty state when no reports exist', () => {
    vi.mocked(useLearningReport).mockReturnValue({
      report: null,
      isLoading: false,
      isError: false,
      error: null,
    });
    vi.mocked(useLearningReports).mockReturnValue({
      data: undefined,
    } as ReturnType<typeof useLearningReports>);
    vi.mocked(useTriggerAnalysis).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useTriggerAnalysis>);
    vi.mocked(useConfigProposals).mockReturnValue({
      data: undefined,
    } as ReturnType<typeof useConfigProposals>);
    vi.mocked(useApproveProposal).mockReturnValue({ mutate: vi.fn() } as unknown as ReturnType<typeof useApproveProposal>);
    vi.mocked(useDismissProposal).mockReturnValue({ mutate: vi.fn() } as unknown as ReturnType<typeof useDismissProposal>);
    vi.mocked(useRevertProposal).mockReturnValue({ mutate: vi.fn() } as unknown as ReturnType<typeof useRevertProposal>);

    renderWithProviders(<LearningInsightsPanel />);

    expect(screen.getByTestId('learning-empty')).toBeInTheDocument();
    expect(
      screen.getByText('No analysis reports yet. Run your first analysis after a trading session.')
    ).toBeInTheDocument();
    expect(screen.getByTestId('run-analysis-button')).toBeInTheDocument();
  });

  it('renders disabled state when enabled=false', () => {
    // Hooks still need to be mocked (called unconditionally due to rules of hooks)
    vi.mocked(useLearningReport).mockReturnValue({
      report: null,
      isLoading: false,
      isError: false,
      error: null,
    });
    vi.mocked(useLearningReports).mockReturnValue({
      data: undefined,
    } as ReturnType<typeof useLearningReports>);
    vi.mocked(useTriggerAnalysis).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useTriggerAnalysis>);
    vi.mocked(useConfigProposals).mockReturnValue({
      data: undefined,
    } as ReturnType<typeof useConfigProposals>);
    vi.mocked(useApproveProposal).mockReturnValue({ mutate: vi.fn() } as unknown as ReturnType<typeof useApproveProposal>);
    vi.mocked(useDismissProposal).mockReturnValue({ mutate: vi.fn() } as unknown as ReturnType<typeof useDismissProposal>);
    vi.mocked(useRevertProposal).mockReturnValue({ mutate: vi.fn() } as unknown as ReturnType<typeof useRevertProposal>);

    renderWithProviders(<LearningInsightsPanel enabled={false} />);

    expect(screen.getByTestId('learning-disabled')).toBeInTheDocument();
    expect(screen.getByText('Learning Loop is disabled in config')).toBeInTheDocument();
  });

  it('passes enabled=false to hooks when isActive is false (lazy loading)', () => {
    setupDefaultMocks();
    renderWithProviders(<LearningInsightsPanel isActive={false} />);

    // useLearningReport should have been called with enabled=false
    expect(useLearningReport).toHaveBeenCalledWith(false);
    // useLearningReports should have been called with enabled=false
    expect(useLearningReports).toHaveBeenCalledWith(undefined, undefined, false);
    // useConfigProposals should have been called with enabled=false
    expect(useConfigProposals).toHaveBeenCalledWith(undefined, false);
  });

  it('triggers analysis on Run Analysis button click', () => {
    const { mutateFn } = setupDefaultMocks();

    // Override to show empty state (which has the button)
    vi.mocked(useLearningReport).mockReturnValue({
      report: null,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<LearningInsightsPanel />);

    const button = screen.getByTestId('run-analysis-button');
    fireEvent.click(button);

    expect(mutateFn).toHaveBeenCalled();
  });

  it('shows loading spinner on Run Analysis button when mutation is pending', () => {
    setupDefaultMocks();
    vi.mocked(useTriggerAnalysis).mockReturnValue({
      mutate: vi.fn(),
      isPending: true,
    } as unknown as ReturnType<typeof useTriggerAnalysis>);
    // Show empty state to expose the button
    vi.mocked(useLearningReport).mockReturnValue({
      report: null,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<LearningInsightsPanel />);

    const button = screen.getByTestId('run-analysis-button');
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent('Running...');
  });

  it('shows data quality preamble with known gaps', () => {
    setupDefaultMocks();
    vi.mocked(useLearningReport).mockReturnValue({
      report: {
        ...mockReport,
        data_quality: {
          ...mockReport.data_quality,
          known_data_gaps: ['2026-03-15: market holiday', '2026-03-20: data outage'],
        },
      },
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<LearningInsightsPanel />);

    expect(screen.getByText(/Known gaps:/)).toBeInTheDocument();
    expect(screen.getByText(/market holiday/)).toBeInTheDocument();
  });
});
