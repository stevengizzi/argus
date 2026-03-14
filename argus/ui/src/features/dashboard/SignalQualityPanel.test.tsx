/**
 * Tests for SignalQualityPanel component.
 *
 * Sprint 24 Session 10.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SignalQualityPanel } from './SignalQualityPanel';

// Mock Recharts
vi.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mock-bar-chart">{children}</div>
  ),
  Bar: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mock-bar">{children}</div>
  ),
  XAxis: () => <div />,
  YAxis: () => <div />,
  Cell: () => <div data-testid="mock-cell" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

const mockUseQualityDistribution = vi.fn();
vi.mock('../../hooks/useQuality', () => ({
  useQualityDistribution: () => mockUseQualityDistribution(),
}));

describe('SignalQualityPanel', () => {
  it('renders histogram bars per grade', () => {
    mockUseQualityDistribution.mockReturnValue({
      data: {
        grades: { 'A+': 2, 'A': 5, 'A-': 3, 'B+': 4, 'B': 2, 'B-': 1, 'C+': 1, 'C': 0 },
        total: 18,
        filtered: 2,
      },
      isLoading: false,
    });

    render(<SignalQualityPanel />);

    expect(screen.getByTestId('signal-quality-histogram')).toBeInTheDocument();
  });

  it('shows passed and filtered count text', () => {
    mockUseQualityDistribution.mockReturnValue({
      data: {
        grades: { 'A+': 2, 'A': 5, 'A-': 3, 'B+': 4, 'B': 2, 'B-': 1, 'C+': 1, 'C': 0 },
        total: 18,
        filtered: 3,
      },
      isLoading: false,
    });

    render(<SignalQualityPanel />);

    const counter = screen.getByTestId('signal-quality-counter');
    expect(counter).toHaveTextContent('Signals today: 15 passed / 3 filtered');
  });

  it('shows empty state message', () => {
    mockUseQualityDistribution.mockReturnValue({
      data: { grades: {}, total: 0, filtered: 0 },
      isLoading: false,
    });

    render(<SignalQualityPanel />);

    expect(screen.getByTestId('signal-quality-empty')).toBeInTheDocument();
    expect(screen.getByText('No quality data yet')).toBeInTheDocument();
  });

  it('shows loading skeleton', () => {
    mockUseQualityDistribution.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    const { container } = render(<SignalQualityPanel />);

    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });
});
