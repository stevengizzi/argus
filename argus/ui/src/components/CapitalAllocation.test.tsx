/**
 * CapitalAllocation component tests.
 *
 * Sprint 18.75 Fix Session B: Updated for custom SVG donut implementation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
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
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        transition: _transition,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        whileHover: _whileHover,
        ...props
      }: React.HTMLAttributes<HTMLDivElement> & {
        initial?: unknown;
        animate?: unknown;
        exit?: unknown;
        variants?: unknown;
        transition?: unknown;
        whileHover?: unknown;
      }) => <div {...props}>{children}</div>,
      // Mock motion.path for AllocationDonut fill arcs
      path: ({
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        initial: _initial,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        animate: _animate,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        transition: _transition,
        ...props
      }: React.SVGAttributes<SVGPathElement> & {
        initial?: unknown;
        animate?: unknown;
        transition?: unknown;
      }) => <path {...props} />,
    },
  };
});

// Mock Zustand store
let mockViewMode = 'donut';
vi.mock('../stores/capitalAllocationUI', () => ({
  useCapitalAllocationUIStore: vi.fn((selector) =>
    selector({
      viewMode: mockViewMode,
      setViewMode: vi.fn((mode: string) => { mockViewMode = mode; }),
    })
  ),
}));

// Mock media query hook
vi.mock('../hooks/useMediaQuery', () => ({
  useMediaQuery: vi.fn(() => false),
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

// Four-strategy allocation (Sprint 20)
const mockFourStrategyAllocations = [
  {
    strategy_id: 'orb_breakout',
    allocation_pct: 0.20,
    allocation_dollars: 20000,
    deployed_pct: 0.08,
    deployed_capital: 8000,
    is_throttled: false,
  },
  {
    strategy_id: 'orb_scalp',
    allocation_pct: 0.20,
    allocation_dollars: 20000,
    deployed_pct: 0.04,
    deployed_capital: 4000,
    is_throttled: false,
  },
  {
    strategy_id: 'vwap_reclaim',
    allocation_pct: 0.20,
    allocation_dollars: 20000,
    deployed_pct: 0.06,
    deployed_capital: 6000,
    is_throttled: false,
  },
  {
    strategy_id: 'afternoon_momentum',
    allocation_pct: 0.20,
    allocation_dollars: 20000,
    deployed_pct: 0.05,
    deployed_capital: 5000,
    is_throttled: false,
  },
];

describe('CapitalAllocation', () => {
  beforeEach(() => {
    mockViewMode = 'donut';
    vi.clearAllMocks();
  });

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

    // Donut view shows the SVG element
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
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

  it('shows legend items for strategies in donut view', () => {
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

  it('renders with four strategies (Sprint 20)', () => {
    render(
      <CapitalAllocation
        allocations={mockFourStrategyAllocations}
        cashReservePct={0.2}
        totalEquity={100000}
      />
    );

    // Should show all four strategies in legend
    // (AllocationDonut uses shortened display names)
    expect(screen.getByText('ORB Breakout')).toBeInTheDocument();
    expect(screen.getByText('ORB Scalp')).toBeInTheDocument();
    expect(screen.getByText('VWAP Reclaim')).toBeInTheDocument();
    expect(screen.getByText('Afternoon Mom')).toBeInTheDocument();
    expect(screen.getByText('Reserve')).toBeInTheDocument();
  });

  it('renders four strategy segments in SVG', () => {
    const { container } = render(
      <CapitalAllocation
        allocations={mockFourStrategyAllocations}
        cashReservePct={0.2}
        totalEquity={100000}
      />
    );

    // SVG should have track paths for all segments (4 strategies + 1 reserve)
    const trackPaths = container.querySelectorAll('svg path');
    // At minimum: 5 track segments + fill arcs
    expect(trackPaths.length).toBeGreaterThanOrEqual(5);
  });

  it('shows center text with deployed percentage', () => {
    render(
      <CapitalAllocation
        allocations={mockAllocations}
        cashReservePct={0.2}
        totalEquity={100000}
        totalDeployedPct={0.15}
      />
    );

    // Center should show deployed percentage
    expect(screen.getByText('15%')).toBeInTheDocument();
    expect(screen.getByText('Deployed')).toBeInTheDocument();
  });
});

describe('CapitalAllocation - Bars view', () => {
  beforeEach(() => {
    mockViewMode = 'bars';
    vi.clearAllMocks();
  });

  it('renders bars view when viewMode is bars', async () => {
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

    // Bars view shows strategy names with bars
    expect(screen.getAllByText('ORB Breakout').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Reserve').length).toBeGreaterThan(0);

    // Should show the legend for bars
    expect(screen.getByText('Deployed')).toBeInTheDocument();
    expect(screen.getByText('Available')).toBeInTheDocument();
  });
});
