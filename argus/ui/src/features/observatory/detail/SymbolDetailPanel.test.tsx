/**
 * Tests for Observatory detail panel: SymbolDetailPanel, SymbolConditionGrid,
 * and SymbolStrategyHistory.
 *
 * Sprint 25, Session 4a.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { SymbolDetailPanel } from './SymbolDetailPanel';
import { SymbolConditionGrid } from './SymbolConditionGrid';
import { SymbolStrategyHistory } from './SymbolStrategyHistory';
import type { ObservatoryJourneyEvent } from '../../../api/client';

vi.mock('../../../api/client', () => ({
  getSymbolJourney: vi.fn().mockResolvedValue({
    symbol: 'AAPL',
    events: [],
    count: 0,
    date: '2026-03-17',
    timestamp: '2026-03-17T14:30:00Z',
  }),
}));

function createQueryWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('SymbolDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders when symbol is selected', () => {
    render(
      <SymbolDetailPanel selectedSymbol="AAPL" selectedTierIndex={3} onClose={vi.fn()} />,
      { wrapper: createQueryWrapper() }
    );

    expect(screen.getByTestId('symbol-detail-panel')).toBeInTheDocument();
    expect(screen.getByTestId('detail-symbol-name')).toHaveTextContent('AAPL');
  });

  it('is hidden when no symbol selected', () => {
    render(
      <SymbolDetailPanel selectedSymbol={null} selectedTierIndex={0} onClose={vi.fn()} />,
      { wrapper: createQueryWrapper() }
    );

    expect(screen.queryByTestId('symbol-detail-panel')).not.toBeInTheDocument();
  });

  it('updates content when symbol changes without re-animation', () => {
    const { rerender } = render(
      <SymbolDetailPanel selectedSymbol="AAPL" selectedTierIndex={3} onClose={vi.fn()} />,
      { wrapper: createQueryWrapper() }
    );

    expect(screen.getByTestId('detail-symbol-name')).toHaveTextContent('AAPL');

    rerender(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <SymbolDetailPanel selectedSymbol="TSLA" selectedTierIndex={3} onClose={vi.fn()} />
      </QueryClientProvider>
    );

    expect(screen.getByTestId('detail-symbol-name')).toHaveTextContent('TSLA');
    // Panel should still be in the DOM (no close/reopen)
    expect(screen.getByTestId('symbol-detail-panel')).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(
      <SymbolDetailPanel selectedSymbol="AAPL" selectedTierIndex={0} onClose={onClose} />,
      { wrapper: createQueryWrapper() }
    );

    fireEvent.click(screen.getByTestId('detail-close-button'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('renders pipeline badge with correct tier name', () => {
    render(
      <SymbolDetailPanel selectedSymbol="NVDA" selectedTierIndex={3} onClose={vi.fn()} />,
      { wrapper: createQueryWrapper() }
    );

    expect(screen.getByTestId('detail-pipeline-badge')).toHaveTextContent('Evaluating');
  });

  it('renders all detail sections', () => {
    render(
      <SymbolDetailPanel selectedSymbol="AAPL" selectedTierIndex={0} onClose={vi.fn()} />,
      { wrapper: createQueryWrapper() }
    );

    expect(screen.getByTestId('detail-quality-section')).toBeInTheDocument();
    expect(screen.getByTestId('detail-market-data')).toBeInTheDocument();
    expect(screen.getByTestId('detail-catalyst-section')).toBeInTheDocument();
    expect(screen.getByTestId('detail-chart-slot')).toBeInTheDocument();
  });
});

describe('SymbolConditionGrid', () => {
  const mockEventsWithConditions: ObservatoryJourneyEvent[] = [
    {
      timestamp: '2026-03-17T14:30:00Z',
      strategy: 'orb_breakout',
      event_type: 'ENTRY_EVALUATION',
      result: 'FAIL',
      metadata: {
        conditions_detail: [
          { name: 'Volume > threshold', passed: true, actual_value: '1.5M', required_value: '1M' },
          { name: 'ATR ratio', passed: false, actual_value: '0.8', required_value: '1.2' },
          { name: 'VWAP alignment', passed: true, actual_value: 'above', required_value: 'above' },
        ],
      },
    },
  ];

  it('shows pass/fail colors correctly', () => {
    render(<SymbolConditionGrid events={mockEventsWithConditions} />);

    const grid = screen.getByTestId('condition-grid');
    const rows = within(grid).getAllByTestId('condition-row');
    expect(rows.length).toBe(3);

    // Passed conditions sorted first
    const passedBadges = within(grid).getAllByTestId('condition-pass');
    expect(passedBadges).toHaveLength(2);

    const failedBadges = within(grid).getAllByTestId('condition-fail');
    expect(failedBadges).toHaveLength(1);
  });

  it('shows gray for inactive conditions', () => {
    const eventsWithInactive: ObservatoryJourneyEvent[] = [
      {
        timestamp: '2026-03-17T14:30:00Z',
        strategy: 'afmo',
        event_type: 'ENTRY_EVALUATION',
        result: 'INFO',
        metadata: {
          conditions_detail: [
            { name: 'Window check', passed: null, actual_value: null, required_value: null },
          ],
        },
      },
    ];

    render(<SymbolConditionGrid events={eventsWithInactive} />);

    expect(screen.getByTestId('condition-inactive')).toBeInTheDocument();
  });

  it('shows empty state when no events', () => {
    render(<SymbolConditionGrid events={[]} />);
    expect(screen.getByTestId('condition-grid-empty')).toHaveTextContent('No evaluation data');
  });
});

describe('SymbolStrategyHistory', () => {
  const mockEvents: ObservatoryJourneyEvent[] = [
    {
      timestamp: '2026-03-17T14:30:00Z',
      strategy: 'orb_breakout',
      event_type: 'ENTRY_EVALUATION',
      result: 'PASS',
      metadata: { reason: 'All conditions met' },
    },
    {
      timestamp: '2026-03-17T14:35:00Z',
      strategy: 'vwap_reclaim',
      event_type: 'ENTRY_EVALUATION',
      result: 'FAIL',
      metadata: { reason: 'Volume too low' },
    },
    {
      timestamp: '2026-03-17T14:32:00Z',
      strategy: 'orb_breakout',
      event_type: 'SIGNAL_GENERATED',
      result: 'INFO',
      metadata: {},
    },
  ];

  it('renders events in chronological order (newest first)', () => {
    render(<SymbolStrategyHistory events={mockEvents} />);

    const eventElements = screen.getAllByTestId('history-event');
    expect(eventElements).toHaveLength(3);

    // First event should be newest (vwap_reclaim at 14:35 UTC)
    expect(eventElements[0]).toHaveTextContent('vwap_reclaim');
    // Last should be oldest (orb_breakout at 14:30 UTC)
    expect(eventElements[2]).toHaveTextContent('All conditions met');
  });

  it('shows empty state when no events', () => {
    render(<SymbolStrategyHistory events={[]} />);
    expect(screen.getByTestId('strategy-history-empty')).toHaveTextContent('No evaluation history');
  });
});
