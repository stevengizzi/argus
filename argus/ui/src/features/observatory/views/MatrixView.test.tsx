/**
 * Tests for Matrix view — condition heatmap, virtual scroll, keyboard nav.
 *
 * Sprint 25, Sessions 5a + 5b.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MatrixView } from './MatrixView';

const mockClosestMisses = vi.fn();

vi.mock('../../../api/client', () => ({
  getObservatoryClosestMisses: (...args: unknown[]) => mockClosestMisses(...args),
  getToken: () => 'mock-token',
}));

// Mock WebSocket globally
const mockWsInstances: Array<{
  onopen: (() => void) | null;
  onmessage: ((e: { data: string }) => void) | null;
  send: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
  readyState: number;
}> = [];

class MockWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  onclose: ((e: unknown) => void) | null = null;
  send = vi.fn();
  close = vi.fn();
  readyState = 1;

  constructor() {
    mockWsInstances.push(this);
  }

  static readonly OPEN = 1;
  static readonly CONNECTING = 0;
}

vi.stubGlobal('WebSocket', MockWebSocket);

function makeCondition(
  name: string,
  passed: boolean,
  actual: string | number | null = '1.5',
  required: string | number | null = '1.0',
) {
  return { name, passed, actual_value: actual, required_value: required };
}

function makeEntry(
  symbol: string,
  strategy: string,
  conditionsPassed: number,
  conditionsTotal: number,
  conditions = [
    makeCondition('volume', conditionsPassed >= 1, '2.5M', '1M'),
    makeCondition('gap_pct', conditionsPassed >= 2, '3.2%', '2%'),
    makeCondition('atr_ratio', conditionsPassed >= 3, '0.8', '1.0'),
  ],
) {
  return {
    symbol,
    strategy,
    conditions_passed: conditionsPassed,
    conditions_total: conditionsTotal,
    conditions_detail: conditions,
    timestamp: '2026-03-17T14:30:00Z',
  };
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe('MatrixView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWsInstances.length = 0;
  });

  it('renders header row with condition columns', async () => {
    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [makeEntry('AAPL', 'orb_breakout', 2, 3)],
      count: 1,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView
        selectedTier={3}
        selectedSymbol={null}
        onSelectSymbol={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('matrix-header-row')).toBeInTheDocument();
    });

    expect(screen.getByTestId('matrix-col-volume')).toBeInTheDocument();
    expect(screen.getByTestId('matrix-col-gap_pct')).toBeInTheDocument();
    expect(screen.getByTestId('matrix-col-atr_ratio')).toBeInTheDocument();
  });

  it('renders correct cell colors for pass/fail/inactive', async () => {
    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [
        makeEntry('TSLA', 'orb_breakout', 2, 3, [
          makeCondition('volume', true, '2.5M', '1M'),
          makeCondition('gap_pct', false, '1.5%', '2%'),
          makeCondition('window', false, null, null),
        ]),
      ],
      count: 1,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView
        selectedTier={3}
        selectedSymbol={null}
        onSelectSymbol={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('matrix-row-TSLA')).toBeInTheDocument();
    });

    const passCell = screen.getByTestId('condition-cell-volume');
    expect(passCell.dataset.passed).toBe('true');
    expect(passCell.dataset.inactive).toBe('false');

    const failCell = screen.getByTestId('condition-cell-gap_pct');
    expect(failCell.dataset.passed).toBe('false');
    expect(failCell.dataset.inactive).toBe('false');

    const inactiveCell = screen.getByTestId('condition-cell-window');
    expect(inactiveCell.dataset.inactive).toBe('true');
  });

  it('clicking a row calls onSelectSymbol', async () => {
    const onSelectSymbol = vi.fn();

    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [makeEntry('NVDA', 'orb_breakout', 3, 3)],
      count: 1,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView
        selectedTier={3}
        selectedSymbol={null}
        onSelectSymbol={onSelectSymbol}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('matrix-row-NVDA')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('matrix-row-NVDA'));
    expect(onSelectSymbol).toHaveBeenCalledWith('NVDA');
  });

  it('sorts rows by conditions_passed descending then alphabetical', async () => {
    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [
        makeEntry('LOW', 'orb_breakout', 1, 3),
        makeEntry('HIGH', 'orb_breakout', 3, 3),
        makeEntry('MID', 'orb_breakout', 2, 3),
      ],
      count: 3,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView
        selectedTier={3}
        selectedSymbol={null}
        onSelectSymbol={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('matrix-row-HIGH')).toBeInTheDocument();
    });

    const rows = screen.getAllByTestId(/^matrix-row-/);
    expect(rows[0]).toHaveAttribute('data-testid', 'matrix-row-HIGH');
    expect(rows[1]).toHaveAttribute('data-testid', 'matrix-row-MID');
    expect(rows[2]).toHaveAttribute('data-testid', 'matrix-row-LOW');
  });

  it('renders gray cells for inactive conditions (null actual_value)', async () => {
    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [
        makeEntry('AMD', 'vwap_reclaim', 0, 2, [
          makeCondition('vwap_cross', false, null, null),
          makeCondition('volume', false, null, null),
        ]),
      ],
      count: 1,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView
        selectedTier={3}
        selectedSymbol={null}
        onSelectSymbol={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('matrix-row-AMD')).toBeInTheDocument();
    });

    const vwapCell = screen.getByTestId('condition-cell-vwap_cross');
    expect(vwapCell.dataset.inactive).toBe('true');

    const volumeCell = screen.getByTestId('condition-cell-volume');
    expect(volumeCell.dataset.inactive).toBe('true');
  });

  it('shows empty tier message when no symbols', async () => {
    mockClosestMisses.mockResolvedValue({
      tier: 'traded',
      items: [],
      count: 0,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView
        selectedTier={6}
        selectedSymbol={null}
        onSelectSymbol={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('matrix-empty')).toBeInTheDocument();
    });

    expect(screen.getByText('No symbols at this tier')).toBeInTheDocument();
  });

  it('groups by strategy with headers when multiple strategies present', async () => {
    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [
        makeEntry('AAPL', 'orb_breakout', 2, 3),
        makeEntry('TSLA', 'vwap_reclaim', 1, 2, [
          makeCondition('vwap_cross', true, '151.2', '150.0'),
          makeCondition('volume', false, '0.8M', '1M'),
        ]),
      ],
      count: 2,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView
        selectedTier={3}
        selectedSymbol={null}
        onSelectSymbol={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(
        screen.getByTestId('strategy-header-orb_breakout'),
      ).toBeInTheDocument();
    });

    expect(
      screen.getByTestId('strategy-header-vwap_reclaim'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('matrix-row-AAPL')).toBeInTheDocument();
    expect(screen.getByTestId('matrix-row-TSLA')).toBeInTheDocument();
  });

  // --- Session 5b tests ---

  it('sorts by conditions_passed desc with alphabetical tiebreaker', async () => {
    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [
        makeEntry('TSLA', 'orb_breakout', 2, 3),
        makeEntry('AAPL', 'orb_breakout', 2, 3),
        makeEntry('MSFT', 'orb_breakout', 2, 3),
      ],
      count: 3,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView
        selectedTier={3}
        selectedSymbol={null}
        onSelectSymbol={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('matrix-row-AAPL')).toBeInTheDocument();
    });

    const rows = screen.getAllByTestId(/^matrix-row-/);
    // Same score → alphabetical: AAPL, MSFT, TSLA
    expect(rows[0]).toHaveAttribute('data-testid', 'matrix-row-AAPL');
    expect(rows[1]).toHaveAttribute('data-testid', 'matrix-row-MSFT');
    expect(rows[2]).toHaveAttribute('data-testid', 'matrix-row-TSLA');
  });

  it('Tab advances highlight to next row', async () => {
    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [
        makeEntry('AAPL', 'orb_breakout', 3, 3),
        makeEntry('TSLA', 'orb_breakout', 2, 3),
        makeEntry('NVDA', 'orb_breakout', 1, 3),
      ],
      count: 3,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView
        selectedTier={3}
        selectedSymbol={null}
        onSelectSymbol={vi.fn()}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('matrix-row-AAPL')).toBeInTheDocument();
    });

    // First Tab highlights first row
    act(() => {
      fireEvent.keyDown(window, { key: 'Tab' });
    });
    expect(screen.getByTestId('matrix-row-AAPL').dataset.highlighted).toBe(
      'true',
    );

    // Second Tab advances to next
    act(() => {
      fireEvent.keyDown(window, { key: 'Tab' });
    });
    expect(screen.getByTestId('matrix-row-TSLA').dataset.highlighted).toBe(
      'true',
    );
    expect(screen.getByTestId('matrix-row-AAPL').dataset.highlighted).toBe(
      'false',
    );
  });

  it('highlight tracks symbol across re-sort', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    // Initial data: AAPL at top (3), TSLA second (2)
    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [
        makeEntry('AAPL', 'orb_breakout', 3, 3),
        makeEntry('TSLA', 'orb_breakout', 2, 3),
      ],
      count: 2,
      timestamp: '2026-03-17T14:30:00Z',
    });

    function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );
    }

    render(
      <MatrixView
        selectedTier={3}
        selectedSymbol={null}
        onSelectSymbol={vi.fn()}
      />,
      { wrapper: Wrapper },
    );

    await waitFor(() => {
      expect(screen.getByTestId('matrix-row-AAPL')).toBeInTheDocument();
    });

    // Tab twice to highlight TSLA (second row)
    act(() => {
      fireEvent.keyDown(window, { key: 'Tab' });
    });
    act(() => {
      fireEvent.keyDown(window, { key: 'Tab' });
    });
    expect(screen.getByTestId('matrix-row-TSLA').dataset.highlighted).toBe(
      'true',
    );

    // Re-sort: TSLA now has higher score and moves to top
    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [
        makeEntry('AAPL', 'orb_breakout', 2, 3),
        makeEntry('TSLA', 'orb_breakout', 3, 3),
      ],
      count: 2,
      timestamp: '2026-03-17T14:30:00Z',
    });

    // Invalidate cache to trigger refetch
    await act(async () => {
      await queryClient.invalidateQueries({
        queryKey: ['observatory', 'closest-misses'],
      });
    });

    await waitFor(() => {
      // After re-sort, TSLA should be first row
      const rows = screen.getAllByTestId(/^matrix-row-/);
      expect(rows[0]).toHaveAttribute('data-testid', 'matrix-row-TSLA');
    });

    // TSLA should still be highlighted after position change
    expect(screen.getByTestId('matrix-row-TSLA').dataset.highlighted).toBe(
      'true',
    );
  });

  it('Enter on highlighted row selects the symbol', async () => {
    const onSelectSymbol = vi.fn();

    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [
        makeEntry('AAPL', 'orb_breakout', 3, 3),
        makeEntry('TSLA', 'orb_breakout', 2, 3),
      ],
      count: 2,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView
        selectedTier={3}
        selectedSymbol={null}
        onSelectSymbol={onSelectSymbol}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('matrix-row-AAPL')).toBeInTheDocument();
    });

    // Tab to highlight first row, then Enter to select
    act(() => {
      fireEvent.keyDown(window, { key: 'Tab' });
    });
    act(() => {
      fireEvent.keyDown(window, { key: 'Enter' });
    });

    expect(onSelectSymbol).toHaveBeenCalledWith('AAPL');
  });
});
