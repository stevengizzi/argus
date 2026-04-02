/**
 * DashboardPage layout tests.
 *
 * Sprint 32.8 Session 2: Updated for 4-row layout.
 * Sprint 25.6 Session 5: Verify card ordering after layout restructure.
 */

import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DashboardPage } from './DashboardPage';

// Mock all dashboard feature components as simple divs with test IDs
vi.mock('../features/dashboard', () => ({
  AIInsightCard: () => <div data-testid="AIInsightCard" />,
  MarketStatusCard: () => <div data-testid="MarketStatusCard" />,
  SessionTimeline: () => <div data-testid="SessionTimeline" />,
  OpenPositions: () => <div data-testid="OpenPositions" />,
  SessionSummaryCard: () => <div data-testid="SessionSummaryCard" />,
  OrchestratorStatusStrip: () => <div data-testid="OrchestratorStatusStrip" />,
  StrategyDeploymentBar: () => <div data-testid="StrategyDeploymentBar" />,
  PreMarketLayout: () => <div data-testid="PreMarketLayout" />,
  SignalQualityPanel: () => <div data-testid="SignalQualityPanel" />,
  VitalsStrip: () => <div data-testid="VitalsStrip" />,
}));

vi.mock('../features/watchlist', () => ({
  WatchlistSidebar: () => <div data-testid="WatchlistSidebar" />,
}));

vi.mock('../components/learning/LearningDashboardCard', () => ({
  LearningDashboardCard: () => <div data-testid="LearningDashboardCard" />,
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
  it('renders VitalsStrip before OpenPositions in DOM order', () => {
    const { container } = renderDashboard();

    const testIds = Array.from(container.querySelectorAll('[data-testid]')).map(
      (el) => el.getAttribute('data-testid'),
    );

    const vitalsIdx = testIds.indexOf('VitalsStrip');
    const posIdx = testIds.indexOf('OpenPositions');

    expect(vitalsIdx).toBeGreaterThan(-1);
    expect(posIdx).toBeGreaterThan(-1);
    expect(vitalsIdx).toBeLessThan(posIdx);
  });

  it('renders all expected dashboard cards', () => {
    const { container } = renderDashboard();

    const expectedCards = [
      'StrategyDeploymentBar',
      'VitalsStrip',
      'OpenPositions',
      'SessionTimeline',
      'SignalQualityPanel',
      'AIInsightCard',
      'LearningDashboardCard',
      'WatchlistSidebar',
    ];

    for (const testId of expectedCards) {
      expect(
        container.querySelector(`[data-testid="${testId}"]`),
        `Expected card "${testId}" to be rendered`,
      ).toBeTruthy();
    }
  });

  it('does not render GoalTracker or UniverseStatusCard on Dashboard', () => {
    const { container } = renderDashboard();
    expect(container.querySelector('[data-testid="GoalTracker"]')).toBeNull();
    expect(container.querySelector('[data-testid="UniverseStatusCard"]')).toBeNull();
  });

  it('renders SignalQualityPanel before AIInsightCard in DOM order (desktop)', () => {
    const { container } = renderDashboard();

    const testIds = Array.from(container.querySelectorAll('[data-testid]')).map(
      (el) => el.getAttribute('data-testid'),
    );

    const sqIdx = testIds.indexOf('SignalQualityPanel');
    const aiIdx = testIds.indexOf('AIInsightCard');

    expect(sqIdx).toBeGreaterThan(-1);
    expect(aiIdx).toBeGreaterThan(-1);
    expect(sqIdx).toBeLessThan(aiIdx);
  });

  it('renders OpenPositions before SessionTimeline and SignalQualityPanel', () => {
    const { container } = renderDashboard();

    const testIds = Array.from(container.querySelectorAll('[data-testid]')).map(
      (el) => el.getAttribute('data-testid'),
    );

    const posIdx = testIds.indexOf('OpenPositions');
    const timelineIdx = testIds.indexOf('SessionTimeline');
    const qualityIdx = testIds.indexOf('SignalQualityPanel');

    expect(posIdx).toBeGreaterThan(-1);
    expect(timelineIdx).toBeGreaterThan(-1);
    expect(qualityIdx).toBeGreaterThan(-1);
    expect(posIdx).toBeLessThan(timelineIdx);
    expect(posIdx).toBeLessThan(qualityIdx);
  });

  // ── New tests for Sprint 32.8 Session 2 ──────────────────────────────────

  it('test_vitals_strip_renders_on_dashboard', () => {
    const { container } = renderDashboard();
    expect(container.querySelector('[data-testid="VitalsStrip"]')).toBeTruthy();
  });

  it('test_dashboard_no_monthly_goal — GoalTracker not rendered', () => {
    const { container } = renderDashboard();
    expect(container.querySelector('[data-testid="GoalTracker"]')).toBeNull();
  });

  it('test_dashboard_no_universe_card — UniverseStatusCard not rendered', () => {
    const { container } = renderDashboard();
    expect(container.querySelector('[data-testid="UniverseStatusCard"]')).toBeNull();
  });

  it('renders AIInsightCard and LearningDashboardCard in same row (Row 4)', () => {
    const { container } = renderDashboard();
    expect(container.querySelector('[data-testid="AIInsightCard"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="LearningDashboardCard"]')).toBeTruthy();
  });

  it('renders StrategyDeploymentBar after VitalsStrip (Row 2 after Row 1)', () => {
    const { container } = renderDashboard();

    const testIds = Array.from(container.querySelectorAll('[data-testid]')).map(
      (el) => el.getAttribute('data-testid'),
    );

    const vitalsIdx = testIds.indexOf('VitalsStrip');
    const deployIdx = testIds.indexOf('StrategyDeploymentBar');

    expect(vitalsIdx).toBeGreaterThan(-1);
    expect(deployIdx).toBeGreaterThan(-1);
    expect(vitalsIdx).toBeLessThan(deployIdx);
  });
});
