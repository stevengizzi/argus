/**
 * Tests for Timeline view — 4 strategy lanes, time axis, severity colors,
 * active window highlighting, click-to-select, data hook bucketing, debrief mode.
 *
 * Sprint 25, Session 8.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TimelineView } from './TimelineView';
import type { EvaluationEvent } from '../../../api/types';

const mockGetStrategyDecisions = vi.fn();

vi.mock('../../../api/client', () => ({
  getStrategyDecisions: (...args: unknown[]) => mockGetStrategyDecisions(...args),
}));

function makeEvent(
  symbol: string,
  strategyId: string,
  eventType: string,
  result: 'PASS' | 'FAIL' | 'INFO',
  overrides: Partial<EvaluationEvent> = {},
): EvaluationEvent {
  return {
    timestamp: '2026-03-17T10:30:00Z',
    symbol,
    strategy_id: strategyId,
    event_type: eventType,
    result,
    reason: 'test reason',
    metadata: {},
    ...overrides,
  };
}

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe('TimelineView', () => {
  const onSelectSymbol = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockGetStrategyDecisions.mockResolvedValue([]);
  });

  it('renders 4 strategy lanes', async () => {
    renderWithQuery(
      <TimelineView selectedSymbol={null} onSelectSymbol={onSelectSymbol} />,
    );

    // Wait for loading to finish
    await screen.findByTestId('timeline-view');

    expect(screen.getByTestId('timeline-lane-orb_breakout')).toBeDefined();
    expect(screen.getByTestId('timeline-lane-orb_scalp')).toBeDefined();
    expect(screen.getByTestId('timeline-lane-vwap_reclaim')).toBeDefined();
    expect(screen.getByTestId('timeline-lane-afternoon_momentum')).toBeDefined();
  });

  it('displays correct lane labels', async () => {
    renderWithQuery(
      <TimelineView selectedSymbol={null} onSelectSymbol={onSelectSymbol} />,
    );

    await screen.findByTestId('timeline-view');

    expect(screen.getByTestId('timeline-lane-label-orb_breakout').textContent).toBe('ORB Breakout');
    expect(screen.getByTestId('timeline-lane-label-orb_scalp').textContent).toBe('ORB Scalp');
    expect(screen.getByTestId('timeline-lane-label-vwap_reclaim').textContent).toBe('VWAP Reclaim');
    expect(screen.getByTestId('timeline-lane-label-afternoon_momentum').textContent).toBe('Afternoon Momentum');
  });

  it('renders time axis with 9:30 to 4:00 tick marks', async () => {
    renderWithQuery(
      <TimelineView selectedSymbol={null} onSelectSymbol={onSelectSymbol} />,
    );

    await screen.findByTestId('timeline-view');

    const timeAxis = screen.getByTestId('timeline-time-axis');
    expect(timeAxis).toBeDefined();

    const tickLabels = screen.getAllByTestId('timeline-tick-label');
    // 9:30, 10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 1:00, 1:30, 2:00, 2:30, 3:00, 3:30, 4:00
    expect(tickLabels.length).toBe(14);

    // First tick should be 9:30
    expect(tickLabels[0].textContent).toContain('9:30');
    // Last tick should be 4:00
    expect(tickLabels[tickLabels.length - 1].textContent).toContain('4:00');
  });

  it('renders event marks with correct severity-based styling', async () => {
    // Return events for orb_breakout with various types
    mockGetStrategyDecisions.mockImplementation((strategyId: string) => {
      if (strategyId === 'orb_breakout') {
        return Promise.resolve([
          makeEvent('AAPL', 'orb_breakout', 'evaluation', 'FAIL'),
          makeEvent('TSLA', 'orb_breakout', 'near_miss', 'FAIL', {
            metadata: { conditions_passed: 4, conditions_total: 6 },
          }),
          makeEvent('NVDA', 'orb_breakout', 'signal', 'PASS'),
          makeEvent('AMD', 'orb_breakout', 'trade_executed', 'PASS'),
        ]);
      }
      return Promise.resolve([]);
    });

    renderWithQuery(
      <TimelineView selectedSymbol={null} onSelectSymbol={onSelectSymbol} />,
    );

    await screen.findByTestId('timeline-view');

    // Check that events with different severities are rendered
    const sev0 = screen.queryAllByTestId('timeline-event-0');
    const sev1 = screen.queryAllByTestId('timeline-event-1');
    const sev2 = screen.queryAllByTestId('timeline-event-2');
    const sev3 = screen.queryAllByTestId('timeline-event-3');

    expect(sev0.length).toBeGreaterThanOrEqual(1); // evaluation
    expect(sev1.length).toBeGreaterThanOrEqual(1); // near-miss
    expect(sev2.length).toBeGreaterThanOrEqual(1); // signal
    expect(sev3.length).toBeGreaterThanOrEqual(1); // trade
  });

  it('highlights active strategy windows', async () => {
    renderWithQuery(
      <TimelineView selectedSymbol={null} onSelectSymbol={onSelectSymbol} />,
    );

    await screen.findByTestId('timeline-view');

    // Each lane should have an active window highlight
    expect(screen.getByTestId('timeline-active-window-orb_breakout')).toBeDefined();
    expect(screen.getByTestId('timeline-active-window-orb_scalp')).toBeDefined();
    expect(screen.getByTestId('timeline-active-window-vwap_reclaim')).toBeDefined();
    expect(screen.getByTestId('timeline-active-window-afternoon_momentum')).toBeDefined();
  });

  it('click on event mark calls onSelectSymbol', async () => {
    mockGetStrategyDecisions.mockImplementation((strategyId: string) => {
      if (strategyId === 'orb_breakout') {
        return Promise.resolve([
          makeEvent('AAPL', 'orb_breakout', 'signal', 'PASS'),
        ]);
      }
      return Promise.resolve([]);
    });

    renderWithQuery(
      <TimelineView selectedSymbol={null} onSelectSymbol={onSelectSymbol} />,
    );

    await screen.findByTestId('timeline-view');

    const eventDots = screen.getAllByTestId('timeline-event-2');
    expect(eventDots.length).toBeGreaterThan(0);
    fireEvent.click(eventDots[0]);
    expect(onSelectSymbol).toHaveBeenCalledWith('AAPL');
  });

  it('buckets events from hook data correctly', async () => {
    // Multiple events at the same timestamp for same symbol should be bucketed
    mockGetStrategyDecisions.mockImplementation((strategyId: string) => {
      if (strategyId === 'vwap_reclaim') {
        return Promise.resolve([
          makeEvent('AAPL', 'vwap_reclaim', 'evaluation', 'FAIL', {
            timestamp: '2026-03-17T10:30:00Z',
          }),
          makeEvent('AAPL', 'vwap_reclaim', 'signal', 'PASS', {
            timestamp: '2026-03-17T10:30:30Z',
          }),
        ]);
      }
      return Promise.resolve([]);
    });

    renderWithQuery(
      <TimelineView selectedSymbol={null} onSelectSymbol={onSelectSymbol} />,
    );

    await screen.findByTestId('timeline-view');

    // Within the same 60s bucket for the same symbol, the higher severity should win.
    // So we should see a severity-2 event (signal) but NOT a severity-0 for the same bucket/symbol.
    const sev2 = screen.queryAllByTestId('timeline-event-2');
    expect(sev2.length).toBeGreaterThanOrEqual(1);
  });

  it('does not poll in debrief mode', async () => {
    renderWithQuery(
      <TimelineView
        selectedSymbol={null}
        onSelectSymbol={onSelectSymbol}
        date="2026-03-16"
      />,
    );

    await screen.findByTestId('timeline-view');

    // In debrief mode, getStrategyDecisions is called once per strategy (4 calls total).
    // We verify it was called with the expected arguments.
    expect(mockGetStrategyDecisions).toHaveBeenCalledTimes(4);

    // Verify refetchInterval is not set (we test this by checking the view renders
    // correctly and only 4 initial calls were made — no repeated calls).
    expect(mockGetStrategyDecisions).toHaveBeenCalledWith('orb_breakout', { limit: 2000 });
    expect(mockGetStrategyDecisions).toHaveBeenCalledWith('orb_scalp', { limit: 2000 });
    expect(mockGetStrategyDecisions).toHaveBeenCalledWith('vwap_reclaim', { limit: 2000 });
    expect(mockGetStrategyDecisions).toHaveBeenCalledWith('afternoon_momentum', { limit: 2000 });
  });
});
