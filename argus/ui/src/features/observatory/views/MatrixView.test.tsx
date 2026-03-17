/**
 * Tests for Matrix view — condition heatmap.
 *
 * Sprint 25, Session 5a.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MatrixView } from './MatrixView';

const mockClosestMisses = vi.fn();

vi.mock('../../../api/client', () => ({
  getObservatoryClosestMisses: (...args: unknown[]) => mockClosestMisses(...args),
}));

function makeCondition(name: string, passed: boolean, actual: string | number | null = '1.5', required: string | number | null = '1.0') {
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
  ]
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
  });

  it('renders header row with condition columns', async () => {
    mockClosestMisses.mockResolvedValue({
      tier: 'evaluating',
      items: [
        makeEntry('AAPL', 'orb_breakout', 2, 3),
      ],
      count: 1,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView selectedTier={3} selectedSymbol={null} onSelectSymbol={vi.fn()} />,
      { wrapper: createWrapper() }
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
          makeCondition('window', false, null, null), // inactive (gray)
        ]),
      ],
      count: 1,
      timestamp: '2026-03-17T14:30:00Z',
    });

    render(
      <MatrixView selectedTier={3} selectedSymbol={null} onSelectSymbol={vi.fn()} />,
      { wrapper: createWrapper() }
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
      <MatrixView selectedTier={3} selectedSymbol={null} onSelectSymbol={onSelectSymbol} />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(screen.getByTestId('matrix-row-NVDA')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('matrix-row-NVDA'));
    expect(onSelectSymbol).toHaveBeenCalledWith('NVDA');
  });

  it('sorts rows by conditions_passed descending', async () => {
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
      <MatrixView selectedTier={3} selectedSymbol={null} onSelectSymbol={vi.fn()} />,
      { wrapper: createWrapper() }
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
      <MatrixView selectedTier={3} selectedSymbol={null} onSelectSymbol={vi.fn()} />,
      { wrapper: createWrapper() }
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
      <MatrixView selectedTier={6} selectedSymbol={null} onSelectSymbol={vi.fn()} />,
      { wrapper: createWrapper() }
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
      <MatrixView selectedTier={3} selectedSymbol={null} onSelectSymbol={vi.fn()} />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(screen.getByTestId('strategy-header-orb_breakout')).toBeInTheDocument();
    });

    expect(screen.getByTestId('strategy-header-vwap_reclaim')).toBeInTheDocument();
    expect(screen.getByTestId('matrix-row-AAPL')).toBeInTheDocument();
    expect(screen.getByTestId('matrix-row-TSLA')).toBeInTheDocument();
  });
});
