/**
 * Tests for QualityDistributionCard component.
 *
 * Sprint 24 Session 10.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QualityDistributionCard } from './QualityDistributionCard';

// Mock Recharts to avoid canvas/SVG measurement issues in test env
vi.mock('recharts', () => ({
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mock-pie-chart">{children}</div>
  ),
  Pie: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mock-pie">{children}</div>
  ),
  Cell: () => <div data-testid="mock-cell" />,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

const mockUseQualityDistribution = vi.fn();
vi.mock('../../hooks/useQuality', () => ({
  useQualityDistribution: () => mockUseQualityDistribution(),
}));

describe('QualityDistributionCard', () => {
  it('renders with mock data', () => {
    mockUseQualityDistribution.mockReturnValue({
      data: {
        grades: { 'A+': 2, 'A': 3, 'A-': 1, 'B+': 4, 'B': 2, 'B-': 1, 'C+': 0, 'C': 0 },
        total: 13,
        filtered: 0,
      },
      isLoading: false,
    });

    render(<QualityDistributionCard />);

    expect(screen.getByTestId('quality-distribution-chart')).toBeInTheDocument();
    expect(screen.getByText('13')).toBeInTheDocument();
    expect(screen.getByText('signals')).toBeInTheDocument();
  });

  it('shows empty state message', () => {
    mockUseQualityDistribution.mockReturnValue({
      data: { grades: {}, total: 0, filtered: 0 },
      isLoading: false,
    });

    render(<QualityDistributionCard />);

    expect(screen.getByTestId('quality-distribution-empty')).toBeInTheDocument();
    expect(screen.getByText('No quality data yet')).toBeInTheDocument();
  });

  it('shows empty state when data is null', () => {
    mockUseQualityDistribution.mockReturnValue({
      data: null,
      isLoading: false,
    });

    render(<QualityDistributionCard />);

    expect(screen.getByText('No quality data yet')).toBeInTheDocument();
  });

  it('shows loading skeleton', () => {
    mockUseQualityDistribution.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    const { container } = render(<QualityDistributionCard />);

    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('shows filtered count when signals were filtered', () => {
    mockUseQualityDistribution.mockReturnValue({
      data: {
        grades: { 'A+': 2, 'A': 1, 'B+': 3, 'C+': 2, 'C': 1 },
        total: 9,
        filtered: 3,
      },
      isLoading: false,
    });

    render(<QualityDistributionCard />);

    expect(screen.getByText('3 filtered')).toBeInTheDocument();
  });
});
