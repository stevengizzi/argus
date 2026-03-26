/**
 * DashboardPage layout tests.
 *
 * Sprint 25.6 Session 5: Verify card ordering after layout restructure.
 */

import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DashboardPage } from './DashboardPage';

// Mock all dashboard feature components as simple divs with test IDs
vi.mock('../features/dashboard', () => ({
  AccountSummary: () => <div data-testid="AccountSummary" />,
  AIInsightCard: () => <div data-testid="AIInsightCard" />,
  DailyPnlCard: () => <div data-testid="DailyPnlCard" />,
  MarketStatusCard: () => <div data-testid="MarketStatusCard" />,
  TodayStats: () => <div data-testid="TodayStats" />,
  SessionTimeline: () => <div data-testid="SessionTimeline" />,
  OpenPositions: () => <div data-testid="OpenPositions" />,
  RecentTrades: () => <div data-testid="RecentTrades" />,
  HealthMini: () => <div data-testid="HealthMini" />,
  SessionSummaryCard: () => <div data-testid="SessionSummaryCard" />,
  OrchestratorStatusStrip: () => <div data-testid="OrchestratorStatusStrip" />,
  StrategyDeploymentBar: () => <div data-testid="StrategyDeploymentBar" />,
  GoalTracker: () => <div data-testid="GoalTracker" />,
  PreMarketLayout: () => <div data-testid="PreMarketLayout" />,
  UniverseStatusCard: () => <div data-testid="UniverseStatusCard" />,
  SignalQualityPanel: () => <div data-testid="SignalQualityPanel" />,
  VixRegimeCard: () => null, // Returns null when VIX disabled (default mock state)
}));

vi.mock('../features/watchlist', () => ({
  WatchlistSidebar: () => <div data-testid="WatchlistSidebar" />,
}));

// Mock hooks
vi.mock('../hooks/useDashboardSummary', () => ({
  useDashboardSummary: () => ({ data: null }),
}));

vi.mock('../hooks/useCopilotContext', () => ({
  useCopilotContext: vi.fn(),
}));

vi.mock('../hooks/useMediaQuery', () => ({
  useIsMultiColumn: () => true,
  useMediaQuery: () => true, // desktop by default
}));

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('DashboardPage', () => {
  it('renders Positions before Universe and SignalQuality in DOM order', () => {
    const { container } = renderDashboard();

    const testIds = Array.from(container.querySelectorAll('[data-testid]')).map(
      (el) => el.getAttribute('data-testid'),
    );

    const posIdx = testIds.indexOf('OpenPositions');
    const universeIdx = testIds.indexOf('UniverseStatusCard');
    const qualityIdx = testIds.indexOf('SignalQualityPanel');

    expect(posIdx).toBeGreaterThan(-1);
    expect(universeIdx).toBeGreaterThan(-1);
    expect(qualityIdx).toBeGreaterThan(-1);
    expect(posIdx).toBeLessThan(universeIdx);
    expect(posIdx).toBeLessThan(qualityIdx);
  });

  it('renders all expected dashboard cards', () => {
    const { container } = renderDashboard();

    const expectedCards = [
      'OrchestratorStatusStrip',
      'StrategyDeploymentBar',
      'AccountSummary',
      'DailyPnlCard',
      'GoalTracker',
      'OpenPositions',
      'TodayStats',
      'SessionTimeline',
      'AIInsightCard',
      'RecentTrades',
      'HealthMini',
      'UniverseStatusCard',
      'SignalQualityPanel',
      'WatchlistSidebar',
    ];

    for (const testId of expectedCards) {
      expect(
        container.querySelector(`[data-testid="${testId}"]`),
        `Expected card "${testId}" to be rendered`,
      ).toBeTruthy();
    }
  });
});
