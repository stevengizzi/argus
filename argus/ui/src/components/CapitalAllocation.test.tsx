/**
 * CapitalAllocation component tests.
 *
 * Sprint 18.75 Session 3.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CapitalAllocation } from './CapitalAllocation';

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      div: ({
        children,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        initial: _initial,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        animate: _animate,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        exit: _exit,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        variants: _variants,
        ...props
      }: React.HTMLAttributes<HTMLDivElement> & {
        initial?: unknown;
        animate?: unknown;
        exit?: unknown;
        variants?: unknown;
      }) => <div {...props}>{children}</div>,
    },
  };
});

// Mock Recharts to avoid SVG rendering issues
vi.mock('recharts', () => ({
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: () => null,
  Cell: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

// Mock Zustand store
vi.mock('../stores/capitalAllocationUI', () => ({
  useCapitalAllocationUIStore: vi.fn((selector) =>
    selector({
      viewMode: 'donut',
      setViewMode: vi.fn(),
    })
  ),
}));

const mockAllocations = [
  {
    strategy_id: 'orb_breakout',
    allocation_pct: 0.25,
    allocation_dollars: 25000,
    deployed_pct: 0.1,
    deployed_capital: 10000,
    is_throttled: false,
  },
  {
    strategy_id: 'orb_scalp',
    allocation_pct: 0.25,
    allocation_dollars: 25000,
    deployed_pct: 0.05,
    deployed_capital: 5000,
    is_throttled: false,
  },
];

describe('CapitalAllocation', () => {
  it('renders without crashing', () => {
    render(
      <CapitalAllocation
        allocations={mockAllocations}
        cashReservePct={0.2}
        totalEquity={100000}
      />
    );

    expect(screen.getByText('Capital Allocation')).toBeInTheDocument();
  });

  it('renders donut view by default', () => {
    render(
      <CapitalAllocation
        allocations={mockAllocations}
        cashReservePct={0.2}
        totalEquity={100000}
      />
    );

    // Donut view shows the pie chart
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  it('shows segmented tab toggle', () => {
    render(
      <CapitalAllocation
        allocations={mockAllocations}
        cashReservePct={0.2}
        totalEquity={100000}
      />
    );

    expect(screen.getByText('Donut')).toBeInTheDocument();
    expect(screen.getByText('Bars')).toBeInTheDocument();
  });

  it('renders empty state when no allocations', () => {
    render(
      <CapitalAllocation
        allocations={[]}
        cashReservePct={0.2}
        totalEquity={100000}
      />
    );

    expect(screen.getByText('No strategies active')).toBeInTheDocument();
  });

  it('shows legend items for strategies', () => {
    render(
      <CapitalAllocation
        allocations={mockAllocations}
        cashReservePct={0.2}
        totalEquity={100000}
      />
    );

    // Legend should show strategy names
    expect(screen.getByText('ORB Breakout')).toBeInTheDocument();
    expect(screen.getByText('ORB Scalp')).toBeInTheDocument();
    expect(screen.getByText('Reserve')).toBeInTheDocument();
  });
});

describe('CapitalAllocation - Bars view', () => {
  it('renders bars view when viewMode is bars', async () => {
    // Reset the mock to return 'bars' view
    const { useCapitalAllocationUIStore } = await import('../stores/capitalAllocationUI');
    vi.mocked(useCapitalAllocationUIStore).mockImplementation((selector) =>
      selector({
        viewMode: 'bars',
        setViewMode: vi.fn(),
      })
    );

    render(
      <CapitalAllocation
        allocations={mockAllocations}
        cashReservePct={0.2}
        totalEquity={100000}
      />
    );

    // Bars view shows strategy names with bars (renders twice for mobile/desktop)
    expect(screen.getAllByText('ORB Breakout').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Reserve').length).toBeGreaterThan(0);

    // Should show the legend for bars
    expect(screen.getByText('Deployed')).toBeInTheDocument();
    expect(screen.getByText('Available')).toBeInTheDocument();
  });
});
