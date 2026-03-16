/**
 * Tests for StrategyDecisionStream component.
 *
 * Sprint 24.5 Session 4.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StrategyDecisionStream } from './StrategyDecisionStream';
import type { EvaluationEvent } from '../../api/types';

const mockUseStrategyDecisions = vi.fn();
vi.mock('../../hooks/useStrategyDecisions', () => ({
  useStrategyDecisions: (...args: unknown[]) => mockUseStrategyDecisions(...args),
}));

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: Record<string, unknown>) => {
      const { variants: _v, initial: _i, animate: _a, exit: _e, transition: _t, ...htmlProps } = props;
      return <div {...htmlProps}>{children as React.ReactNode}</div>;
    },
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

function makeEvent(overrides: Partial<EvaluationEvent> = {}): EvaluationEvent {
  return {
    timestamp: '2026-03-16T10:30:00-04:00',
    symbol: 'AAPL',
    strategy_id: 'strat_orb_breakout',
    event_type: 'CANDLE_CHECK',
    result: 'PASS',
    reason: 'Volume above threshold',
    metadata: {},
    ...overrides,
  };
}

function renderStream(overrides?: Parameters<typeof mockUseStrategyDecisions>[0]) {
  const onClose = vi.fn();
  const result = render(
    <StrategyDecisionStream strategyId={overrides ?? 'strat_orb_breakout'} onClose={onClose} />
  );
  return { ...result, onClose };
}

describe('StrategyDecisionStream', () => {
  it('renders event list with mock data', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: [
        makeEvent({ symbol: 'AAPL', event_type: 'CANDLE_CHECK', result: 'PASS' }),
        makeEvent({ symbol: 'NVDA', event_type: 'VOLUME_FILTER', result: 'FAIL' }),
        makeEvent({ symbol: 'TSLA', event_type: 'SIGNAL_GENERATED', result: 'INFO' }),
      ],
      isLoading: false,
      error: null,
    });

    renderStream();

    const rows = screen.getAllByTestId('event-row');
    expect(rows).toHaveLength(3);
    expect(screen.getByText('CANDLE_CHECK')).toBeInTheDocument();
    expect(screen.getByText('VOLUME_FILTER')).toBeInTheDocument();
    expect(screen.getByText('SIGNAL_GENERATED')).toBeInTheDocument();
  });

  it('color codes PASS events as green', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: [makeEvent({ result: 'PASS' })],
      isLoading: false,
      error: null,
    });

    renderStream();

    const resultEl = screen.getByTestId('event-result');
    expect(resultEl.className).toContain('text-emerald-400');
  });

  it('color codes FAIL events as red', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: [makeEvent({ result: 'FAIL' })],
      isLoading: false,
      error: null,
    });

    renderStream();

    const resultEl = screen.getByTestId('event-result');
    expect(resultEl.className).toContain('text-red-400');
  });

  it('color codes INFO events as amber', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: [makeEvent({ result: 'INFO', event_type: 'STATUS_UPDATE' })],
      isLoading: false,
      error: null,
    });

    renderStream();

    const resultEl = screen.getByTestId('event-result');
    expect(resultEl.className).toContain('text-amber-400');
  });

  it('color codes SIGNAL_GENERATED events as blue', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: [makeEvent({ event_type: 'SIGNAL_GENERATED', result: 'PASS' })],
      isLoading: false,
      error: null,
    });

    renderStream();

    const resultEl = screen.getByTestId('event-result');
    expect(resultEl.className).toContain('text-blue-400');
  });

  it('symbol filter filters displayed events', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: [
        makeEvent({ symbol: 'AAPL', event_type: 'CHECK_A' }),
        makeEvent({ symbol: 'NVDA', event_type: 'CHECK_B' }),
        makeEvent({ symbol: 'TSLA', event_type: 'CHECK_C' }),
      ],
      isLoading: false,
      error: null,
    });

    renderStream();

    expect(screen.getAllByTestId('event-row')).toHaveLength(3);

    const select = screen.getByTestId('symbol-filter');
    fireEvent.change(select, { target: { value: 'AAPL' } });

    expect(screen.getAllByTestId('event-row')).toHaveLength(1);
    expect(screen.getByText('CHECK_A')).toBeInTheDocument();
  });

  it('empty state shows awaiting message', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    renderStream();

    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    expect(
      screen.getByText(/Awaiting market data/)
    ).toBeInTheDocument();
  });

  it('loading state shows skeleton', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    renderStream();

    expect(screen.getByTestId('loading-skeleton')).toBeInTheDocument();
    const { container } = render(
      <StrategyDecisionStream strategyId="strat_orb_breakout" onClose={() => {}} />
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('summary stats show correct counts', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: [
        makeEvent({ symbol: 'AAPL', event_type: 'SIGNAL_GENERATED' }),
        makeEvent({ symbol: 'NVDA', event_type: 'SIGNAL_REJECTED' }),
        makeEvent({ symbol: 'NVDA', event_type: 'SIGNAL_REJECTED' }),
        makeEvent({ symbol: 'TSLA', event_type: 'CANDLE_CHECK' }),
      ],
      isLoading: false,
      error: null,
    });

    renderStream();

    const stats = screen.getByTestId('summary-stats');
    expect(stats).toHaveTextContent('Symbols: 3');
    expect(stats).toHaveTextContent('Signals: 1');
    expect(stats).toHaveTextContent('Rejected: 2');
  });

  it('summary stats reflect symbol filter', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: [
        makeEvent({ symbol: 'AAPL', event_type: 'SIGNAL_GENERATED' }),
        makeEvent({ symbol: 'AAPL', event_type: 'SIGNAL_REJECTED' }),
        makeEvent({ symbol: 'NVDA', event_type: 'SIGNAL_GENERATED' }),
        makeEvent({ symbol: 'NVDA', event_type: 'SIGNAL_REJECTED' }),
        makeEvent({ symbol: 'NVDA', event_type: 'SIGNAL_REJECTED' }),
      ],
      isLoading: false,
      error: null,
    });

    renderStream();

    const stats = screen.getByTestId('summary-stats');
    expect(stats).toHaveTextContent('Signals: 2');
    expect(stats).toHaveTextContent('Rejected: 3');

    const select = screen.getByTestId('symbol-filter');
    fireEvent.change(select, { target: { value: 'AAPL' } });

    expect(stats).toHaveTextContent('Signals: 1');
    expect(stats).toHaveTextContent('Rejected: 1');
  });

  it('close button calls onClose', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    const { onClose } = renderStream();

    const closeBtn = screen.getByTestId('close-button');
    fireEvent.click(closeBtn);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('clicking event row expands metadata', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: [
        makeEvent({
          metadata: { atr_ratio: 1.5, volume: 50000 },
        }),
      ],
      isLoading: false,
      error: null,
    });

    renderStream();

    expect(screen.queryByTestId('event-metadata')).not.toBeInTheDocument();

    const header = screen.getByTestId('event-row-header');
    fireEvent.click(header);

    expect(screen.getByTestId('event-metadata')).toBeInTheDocument();
    expect(screen.getByText(/"atr_ratio": 1.5/)).toBeInTheDocument();
  });

  it('handles API error gracefully', () => {
    mockUseStrategyDecisions.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
    });

    renderStream();

    expect(screen.getByTestId('error-state')).toBeInTheDocument();
    expect(screen.getByText(/Network error/)).toBeInTheDocument();
  });
});
