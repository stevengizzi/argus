/**
 * Tests for UniverseStatusCard component.
 *
 * Sprint 23: NLP Catalyst + Universe Manager
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { UniverseStatusCard } from '../UniverseStatusCard';
import type { UniverseStatusResponse } from '../../../api/types';

// Mock useUniverseStatus hook
const mockUseUniverseStatus = vi.fn();

vi.mock('../../../hooks', () => ({
  useUniverseStatus: () => mockUseUniverseStatus(),
}));

const mockEnabledData: UniverseStatusResponse = {
  enabled: true,
  total_symbols: 5000,
  viable_count: 2847,
  per_strategy_counts: {
    orb_breakout: 1245,
    orb_scalp: 892,
    vwap_reclaim: 1534,
    afternoon_momentum: 743,
  },
  last_refresh: '2026-03-08T14:30:00Z',
  reference_data_age_minutes: 45,
};

const mockDisabledData: UniverseStatusResponse = {
  enabled: false,
  total_symbols: null,
  viable_count: null,
  per_strategy_counts: null,
  last_refresh: null,
  reference_data_age_minutes: null,
};

describe('UniverseStatusCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Universe header', () => {
    mockUseUniverseStatus.mockReturnValue({
      data: mockEnabledData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<UniverseStatusCard />);

    expect(screen.getByText('Universe')).toBeInTheDocument();
  });

  it('renders enabled state with viable count', () => {
    mockUseUniverseStatus.mockReturnValue({
      data: mockEnabledData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<UniverseStatusCard />);

    expect(screen.getByText('2,847')).toBeInTheDocument();
    expect(screen.getByText('viable symbols')).toBeInTheDocument();
  });

  it('renders disabled state when universe manager not enabled', () => {
    mockUseUniverseStatus.mockReturnValue({
      data: mockDisabledData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<UniverseStatusCard />);

    expect(screen.getByText('Universe Manager not enabled')).toBeInTheDocument();
    // Should not show refresh button when disabled
    expect(screen.queryByText('Refresh')).not.toBeInTheDocument();
  });

  it('shows loading skeleton when data is loading', () => {
    mockUseUniverseStatus.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    const { container } = render(<UniverseStatusCard />);

    // Check for skeleton animation
    const pulsingElements = container.querySelectorAll('.animate-pulse');
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  it('shows error state and retry button when fetch fails', () => {
    mockUseUniverseStatus.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('Failed to fetch'),
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<UniverseStatusCard />);

    expect(screen.getByText('Unable to load universe status')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('displays per-strategy counts', () => {
    mockUseUniverseStatus.mockReturnValue({
      data: mockEnabledData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<UniverseStatusCard />);

    // Check that strategy names and counts are displayed
    expect(screen.getByText('orb_breakout')).toBeInTheDocument();
    expect(screen.getByText('1245')).toBeInTheDocument();
    expect(screen.getByText('orb_scalp')).toBeInTheDocument();
    expect(screen.getByText('892')).toBeInTheDocument();
    expect(screen.getByText('vwap_reclaim')).toBeInTheDocument();
    expect(screen.getByText('1534')).toBeInTheDocument();
    expect(screen.getByText('afternoon_momentum')).toBeInTheDocument();
    expect(screen.getByText('743')).toBeInTheDocument();
  });

  it('displays reference data age correctly', () => {
    mockUseUniverseStatus.mockReturnValue({
      data: mockEnabledData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<UniverseStatusCard />);

    expect(screen.getByText('Updated 45 min ago')).toBeInTheDocument();
  });

  it('calls refetch when refresh button is clicked', () => {
    const mockRefetch = vi.fn();
    mockUseUniverseStatus.mockReturnValue({
      data: mockEnabledData,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
      isFetching: false,
    });

    render(<UniverseStatusCard />);

    const refreshButton = screen.getByText('Refresh');
    fireEvent.click(refreshButton);

    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  it('shows spinning refresh icon when fetching', () => {
    mockUseUniverseStatus.mockReturnValue({
      data: mockEnabledData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: true,
    });

    const { container } = render(<UniverseStatusCard />);

    // Check for spinning animation class
    const spinningElements = container.querySelectorAll('.animate-spin');
    expect(spinningElements.length).toBeGreaterThan(0);
  });

  it('formats hours age correctly', () => {
    mockUseUniverseStatus.mockReturnValue({
      data: {
        ...mockEnabledData,
        reference_data_age_minutes: 125, // 2+ hours
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<UniverseStatusCard />);

    expect(screen.getByText('Updated 2h ago')).toBeInTheDocument();
  });

  it('shows "Just now" for very recent data', () => {
    mockUseUniverseStatus.mockReturnValue({
      data: {
        ...mockEnabledData,
        reference_data_age_minutes: 0.5,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isFetching: false,
    });

    render(<UniverseStatusCard />);

    expect(screen.getByText('Updated Just now')).toBeInTheDocument();
  });
});
