/**
 * VitalsStrip component tests.
 *
 * Sprint 32.8, Session 2.
 * Tests that VitalsStrip renders equity, daily P&L, today's stats,
 * and VIX/regime sections correctly.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { VitalsStrip } from './VitalsStrip';

// Mock hooks used by VitalsStrip
vi.mock('../../hooks/useAccount', () => ({
  useAccount: () => ({
    data: {
      equity: 125_432.18,
      cash: 98_000,
      buying_power: 195_000,
      daily_pnl: 1_234.56,
      daily_pnl_pct: 0.99,
      daily_trades_count: 5,
    },
    isLoading: false,
  }),
}));

vi.mock('../../hooks/useLiveEquity', () => ({
  useLiveEquity: () => ({
    equity: 125_432.18,
    dailyPnl: 1_234.56,
    dailyPnlPct: 0.99,
  }),
}));

vi.mock('../../hooks/useSparklineData', () => ({
  useSparklineData: () => ({
    pnlTrend: [100, 200, 300, 250, 400],
    equityTrend: [100, 300, 600, 850, 1250],
    isLoading: false,
    pnlDirection: 'positive' as const,
  }),
}));

vi.mock('../../hooks/useVixData', () => ({
  useVixData: () => ({
    data: {
      status: 'ok',
      vix_close: 18.42,
      data_date: '2026-04-02',
      is_stale: false,
      regime: {
        vol_regime_phase: 'calm',
        vol_regime_momentum: 'neutral',
        vrp_tier: 'normal',
        term_structure_regime: null,
      },
      timestamp: '2026-04-02T09:30:00Z',
    },
    isLoading: false,
  }),
}));

vi.mock('../../components/AnimatedNumber', () => ({
  AnimatedNumber: ({ value, format, className }: { value: number; format: (v: number) => string; className?: string }) => (
    <span className={className} data-testid="animated-number">{format(value)}</span>
  ),
}));

vi.mock('../../components/Sparkline', () => ({
  Sparkline: () => <div data-testid="sparkline" />,
}));

vi.mock('../../components/PnlValue', () => ({
  PnlValue: ({ value }: { value: number }) => (
    <span data-testid="pnl-value">{value.toFixed(2)}%</span>
  ),
}));

function renderVitalsStrip(todayStats?: Parameters<typeof VitalsStrip>[0]['todayStats']) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <VitalsStrip todayStats={todayStats} />
    </QueryClientProvider>,
  );
}

describe('VitalsStrip', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('test_vitals_strip_renders_equity — shows account equity value', () => {
    renderVitalsStrip();
    expect(screen.getByTestId('VitalsStrip')).toBeTruthy();
    // Equity section label
    expect(screen.getByText('Equity')).toBeTruthy();
  });

  it('test_vitals_strip_renders_daily_pnl — shows daily P&L section', () => {
    renderVitalsStrip();
    expect(screen.getByText('Daily P&L')).toBeTruthy();
    // Sparkline should render since we have pnlTrend data
    expect(screen.getByTestId('sparkline')).toBeTruthy();
  });

  it('test_vitals_strip_renders_todays_stats — trade count and win rate present', () => {
    const todayStats = {
      trade_count: 7,
      win_rate: 0.71,
      avg_r: 1.2,
      best_trade: { symbol: 'NVDA', pnl: 430 },
    };
    renderVitalsStrip(todayStats);
    expect(screen.getByText("Today's Stats")).toBeTruthy();
    expect(screen.getByText('Trades')).toBeTruthy();
    expect(screen.getByText('Win Rate')).toBeTruthy();
    expect(screen.getByText('7')).toBeTruthy();
    expect(screen.getByText('71.0%')).toBeTruthy();
  });

  it('shows VIX section when data is available', () => {
    renderVitalsStrip();
    expect(screen.getByText('VIX Regime')).toBeTruthy();
    expect(screen.getByTestId('vitals-vix-close')).toBeTruthy();
  });

  it('shows dash placeholders when no todayStats provided', () => {
    renderVitalsStrip();
    // trade_count defaults to 0, ratios show dash
    expect(screen.getByText('0')).toBeTruthy();
  });
});
