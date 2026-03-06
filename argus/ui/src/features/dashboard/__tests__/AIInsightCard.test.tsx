/**
 * Tests for AIInsightCard component.
 *
 * Sprint 22 Session 6.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AIInsightCard } from '../AIInsightCard';
import type { AIInsightResponse, AIStatusResponse } from '../../../api/types';

// Mock useAIInsight and useAIStatus hooks
const mockUseAIInsight = vi.fn();
const mockUseAIStatus = vi.fn();

vi.mock('../../../hooks', () => ({
  useAIInsight: () => mockUseAIInsight(),
  useAIStatus: () => mockUseAIStatus(),
}));

const mockInsightData: AIInsightResponse = {
  insight: 'Market conditions are favorable today. Consider momentum strategies.',
  generated_at: new Date().toISOString(),
  cached: false,
  message: null,
};

const mockStatusEnabled: AIStatusResponse = {
  enabled: true,
  model: 'claude-3-sonnet',
  usage: null,
};

const mockStatusDisabled: AIStatusResponse = {
  enabled: false,
  model: null,
  usage: null,
};

describe('AIInsightCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders AI Insight header', () => {
    mockUseAIStatus.mockReturnValue({
      data: mockStatusEnabled,
      isLoading: false,
    });
    mockUseAIInsight.mockReturnValue({
      data: mockInsightData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<AIInsightCard />);

    expect(screen.getByText('AI Insight')).toBeInTheDocument();
  });

  it('renders insight text from API response', () => {
    mockUseAIStatus.mockReturnValue({
      data: mockStatusEnabled,
      isLoading: false,
    });
    mockUseAIInsight.mockReturnValue({
      data: mockInsightData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<AIInsightCard />);

    expect(screen.getByText(/Market conditions are favorable/)).toBeInTheDocument();
  });

  it('shows loading skeleton when data is loading', () => {
    mockUseAIStatus.mockReturnValue({
      data: null,
      isLoading: true,
    });
    mockUseAIInsight.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    const { container } = render(<AIInsightCard />);

    // Check for skeleton animation
    const pulsingElements = container.querySelectorAll('.animate-pulse');
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  it('shows AI-disabled state when AI is not enabled', () => {
    mockUseAIStatus.mockReturnValue({
      data: mockStatusDisabled,
      isLoading: false,
    });
    mockUseAIInsight.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<AIInsightCard />);

    expect(screen.getByText('AI insights not available')).toBeInTheDocument();
    // Should not show refresh button when disabled
    expect(screen.queryByText('Refresh')).not.toBeInTheDocument();
  });

  it('shows error state and retry button when fetch fails', () => {
    mockUseAIStatus.mockReturnValue({
      data: mockStatusEnabled,
      isLoading: false,
    });
    mockUseAIInsight.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('Failed to fetch'),
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<AIInsightCard />);

    expect(screen.getByText('Unable to generate insight')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('calls refetch when refresh button is clicked', () => {
    const mockRefetch = vi.fn();
    mockUseAIStatus.mockReturnValue({
      data: mockStatusEnabled,
      isLoading: false,
    });
    mockUseAIInsight.mockReturnValue({
      data: mockInsightData,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
      isFetching: false,
    });

    render(<AIInsightCard />);

    const refreshButton = screen.getByText('Refresh');
    fireEvent.click(refreshButton);

    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  it('shows cached indicator when insight is from cache', () => {
    mockUseAIStatus.mockReturnValue({
      data: mockStatusEnabled,
      isLoading: false,
    });
    mockUseAIInsight.mockReturnValue({
      data: { ...mockInsightData, cached: true },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<AIInsightCard />);

    expect(screen.getByText(/\(cached\)/)).toBeInTheDocument();
  });

  it('shows generated timestamp', () => {
    mockUseAIStatus.mockReturnValue({
      data: mockStatusEnabled,
      isLoading: false,
    });
    mockUseAIInsight.mockReturnValue({
      data: mockInsightData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<AIInsightCard />);

    expect(screen.getByText(/Generated/)).toBeInTheDocument();
  });
});
