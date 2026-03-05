/**
 * Tests for TradeFilters component.
 *
 * Sprint 21.5.1, Session 4.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TradeFilters } from './TradeFilters';
import type { OutcomeFilter } from '../../hooks/useTradeFilters';

// Mock useStrategies hook
vi.mock('../../hooks/useStrategies', () => ({
  useStrategies: () => ({
    data: {
      strategies: [
        { strategy_id: 'strat_orb', name: 'ORB Breakout' },
        { strategy_id: 'strat_scalp', name: 'ORB Scalp' },
      ],
    },
  }),
}));

// Mock useTrades hook (for counts)
vi.mock('../../hooks/useTrades', () => ({
  useTrades: () => ({
    data: { total_count: 100 },
  }),
}));

// Mock the tradeFilters store
const mockSetQuickFilter = vi.fn();
vi.mock('../../stores/tradeFilters', () => ({
  useTradeFiltersStore: () => ({
    quickFilter: 'all',
    setQuickFilter: mockSetQuickFilter,
  }),
  computeDateRangeForQuickFilter: vi.fn((filter: string) => {
    const today = '2026-03-05';
    switch (filter) {
      case 'today':
        return { dateFrom: today, dateTo: today };
      case 'week':
        return { dateFrom: '2026-03-03', dateTo: today }; // Monday of current week
      case 'month':
        return { dateFrom: '2026-03-01', dateTo: today };
      case 'all':
      default:
        return { dateFrom: undefined, dateTo: undefined };
    }
  }),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

interface FilterState {
  strategy_id: string | undefined;
  outcome: OutcomeFilter;
  date_from: string | undefined;
  date_to: string | undefined;
  page: number;
}

describe('TradeFilters', () => {
  const defaultFilters: FilterState = {
    strategy_id: undefined,
    outcome: 'all',
    date_from: undefined,
    date_to: undefined,
    page: 1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders quick filter buttons', () => {
    const onFiltersChange = vi.fn();

    render(
      <TradeFilters filters={defaultFilters} onFiltersChange={onFiltersChange} />,
      { wrapper: createWrapper() }
    );

    // All quick filter buttons should be visible
    expect(screen.getByTestId('quick-filter-today')).toBeInTheDocument();
    expect(screen.getByTestId('quick-filter-week')).toBeInTheDocument();
    expect(screen.getByTestId('quick-filter-month')).toBeInTheDocument();
    expect(screen.getByTestId('quick-filter-all')).toBeInTheDocument();
  });

  it('clicking Today button sets date range to today', () => {
    const onFiltersChange = vi.fn();

    render(
      <TradeFilters filters={defaultFilters} onFiltersChange={onFiltersChange} />,
      { wrapper: createWrapper() }
    );

    // Click the Today button
    fireEvent.click(screen.getByTestId('quick-filter-today'));

    // Should update the quick filter in store
    expect(mockSetQuickFilter).toHaveBeenCalledWith('today');

    // Should call onFiltersChange with today's date for both from and to
    expect(onFiltersChange).toHaveBeenCalledWith({
      date_from: '2026-03-05',
      date_to: '2026-03-05',
    });
  });

  it('clicking Week button sets date range to current week', () => {
    const onFiltersChange = vi.fn();

    render(
      <TradeFilters filters={defaultFilters} onFiltersChange={onFiltersChange} />,
      { wrapper: createWrapper() }
    );

    // Click the Week button
    fireEvent.click(screen.getByTestId('quick-filter-week'));

    // Should update the quick filter in store
    expect(mockSetQuickFilter).toHaveBeenCalledWith('week');

    // Should call onFiltersChange with week date range
    expect(onFiltersChange).toHaveBeenCalledWith({
      date_from: '2026-03-03',
      date_to: '2026-03-05',
    });
  });

  it('clicking Month button sets date range to current month', () => {
    const onFiltersChange = vi.fn();

    render(
      <TradeFilters filters={defaultFilters} onFiltersChange={onFiltersChange} />,
      { wrapper: createWrapper() }
    );

    // Click the Month button
    fireEvent.click(screen.getByTestId('quick-filter-month'));

    // Should update the quick filter in store
    expect(mockSetQuickFilter).toHaveBeenCalledWith('month');

    // Should call onFiltersChange with month date range
    expect(onFiltersChange).toHaveBeenCalledWith({
      date_from: '2026-03-01',
      date_to: '2026-03-05',
    });
  });

  it('clicking All button clears date range', () => {
    const onFiltersChange = vi.fn();

    render(
      <TradeFilters
        filters={{ ...defaultFilters, date_from: '2026-03-01', date_to: '2026-03-05' }}
        onFiltersChange={onFiltersChange}
      />,
      { wrapper: createWrapper() }
    );

    // Click the All button
    fireEvent.click(screen.getByTestId('quick-filter-all'));

    // Should update the quick filter in store
    expect(mockSetQuickFilter).toHaveBeenCalledWith('all');

    // Should call onFiltersChange with undefined dates
    expect(onFiltersChange).toHaveBeenCalledWith({
      date_from: undefined,
      date_to: undefined,
    });
  });

  it('shows Clear button when filters are active', () => {
    const onFiltersChange = vi.fn();

    render(
      <TradeFilters
        filters={{ ...defaultFilters, strategy_id: 'strat_orb' }}
        onFiltersChange={onFiltersChange}
      />,
      { wrapper: createWrapper() }
    );

    // Clear button should be visible
    expect(screen.getByText('Clear')).toBeInTheDocument();
  });

  it('Clear button resets all filters', () => {
    const onFiltersChange = vi.fn();

    render(
      <TradeFilters
        filters={{
          ...defaultFilters,
          strategy_id: 'strat_orb',
          outcome: 'win',
          date_from: '2026-03-01',
          date_to: '2026-03-05',
        }}
        onFiltersChange={onFiltersChange}
      />,
      { wrapper: createWrapper() }
    );

    // Click the Clear button
    fireEvent.click(screen.getByText('Clear'));

    // Should reset quick filter
    expect(mockSetQuickFilter).toHaveBeenCalledWith('all');

    // Should reset all filters
    expect(onFiltersChange).toHaveBeenCalledWith({
      strategy_id: undefined,
      outcome: 'all',
      date_from: undefined,
      date_to: undefined,
    });
  });

  it('does not show Clear button when no filters are active', () => {
    const onFiltersChange = vi.fn();

    render(
      <TradeFilters filters={defaultFilters} onFiltersChange={onFiltersChange} />,
      { wrapper: createWrapper() }
    );

    // Clear button should not be visible
    expect(screen.queryByText('Clear')).not.toBeInTheDocument();
  });
});
