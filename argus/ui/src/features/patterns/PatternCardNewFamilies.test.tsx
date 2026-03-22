/**
 * Tests for new pattern family support in Pattern Library components.
 *
 * Sprint 26, Session 10: Verifies reversal, continuation, and breakout
 * families render correctly in PatternCard, PatternCardGrid, and IncubatorPipeline.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PatternCard } from './PatternCard';
import { PatternCardGrid } from './PatternCardGrid';
import { IncubatorPipeline } from './IncubatorPipeline';
import type { StrategyInfo } from '../../api/types';

// --- Mock data: all 7 strategies ---

function makeStrategy(overrides: Partial<StrategyInfo>): StrategyInfo {
  return {
    strategy_id: 'test_strategy',
    name: 'Test Strategy',
    version: '1.0.0',
    is_active: true,
    pipeline_stage: 'paper_trading',
    allocated_capital: 10000,
    daily_pnl: 0,
    trade_count_today: 0,
    open_positions: 0,
    config_summary: {},
    time_window: '9:30 AM – 10:00 AM',
    family: 'orb_family',
    description_short: 'Test strategy description',
    performance_summary: null,
    backtest_summary: null,
    ...overrides,
  };
}

const ALL_SEVEN_STRATEGIES: StrategyInfo[] = [
  makeStrategy({
    strategy_id: 'orb_breakout',
    name: 'ORB Breakout',
    pipeline_stage: 'paper_trading',
    family: 'orb_family',
    time_window: '9:35–11:30 AM',
  }),
  makeStrategy({
    strategy_id: 'orb_scalp',
    name: 'ORB Scalp',
    pipeline_stage: 'paper_trading',
    family: 'orb_family',
    time_window: '9:35–10:30 AM',
  }),
  makeStrategy({
    strategy_id: 'vwap_reclaim',
    name: 'VWAP Reclaim',
    pipeline_stage: 'paper_trading',
    family: 'momentum',
    time_window: '10:00 AM – 2:00 PM',
  }),
  makeStrategy({
    strategy_id: 'afternoon_momentum',
    name: 'Afternoon Momentum',
    pipeline_stage: 'paper_trading',
    family: 'momentum',
    time_window: '1:00 – 3:55 PM',
  }),
  makeStrategy({
    strategy_id: 'red_to_green',
    name: 'Red-to-Green',
    pipeline_stage: 'exploration',
    family: 'reversal',
    time_window: '9:45 – 11:00 AM',
  }),
  makeStrategy({
    strategy_id: 'bull_flag',
    name: 'Bull Flag',
    pipeline_stage: 'exploration',
    family: 'continuation',
    time_window: '10:00 AM – 2:00 PM',
  }),
  makeStrategy({
    strategy_id: 'flat_top_breakout',
    name: 'Flat-Top Breakout',
    pipeline_stage: 'exploration',
    family: 'breakout',
    time_window: '9:45 – 11:30 AM',
  }),
];

// Mock the Zustand store used by PatternCardGrid
vi.mock('../../stores/patternLibraryUI', () => ({
  usePatternLibraryUI: () => ({
    selectedStrategyId: null,
    activeTab: 'overview',
    filters: { stage: null, family: null, timeWindow: null },
    sortBy: 'name',
    setSelectedStrategy: vi.fn(),
    setActiveTab: vi.fn(),
    setFilter: vi.fn(),
    setSortBy: vi.fn(),
    clearFilters: vi.fn(),
  }),
}));

describe('PatternCard — new family badges', () => {
  it('renders reversal family badge for R2G', () => {
    const r2g = ALL_SEVEN_STRATEGIES.find((s) => s.strategy_id === 'red_to_green')!;

    render(<PatternCard strategy={r2g} isSelected={false} onSelect={vi.fn()} />);

    expect(screen.getByText('Red-to-Green')).toBeInTheDocument();
    expect(screen.getByText('Reversal')).toBeInTheDocument();
    expect(screen.getByText('Explore')).toBeInTheDocument();
  });

  it('renders continuation family badge for Bull Flag', () => {
    const bullFlag = ALL_SEVEN_STRATEGIES.find((s) => s.strategy_id === 'bull_flag')!;

    render(<PatternCard strategy={bullFlag} isSelected={false} onSelect={vi.fn()} />);

    expect(screen.getByText('Bull Flag')).toBeInTheDocument();
    expect(screen.getByText('Continuation')).toBeInTheDocument();
  });

  it('renders breakout family badge for Flat-Top', () => {
    const flatTop = ALL_SEVEN_STRATEGIES.find((s) => s.strategy_id === 'flat_top_breakout')!;

    render(<PatternCard strategy={flatTop} isSelected={false} onSelect={vi.fn()} />);

    expect(screen.getByText('Flat-Top Breakout')).toBeInTheDocument();
    expect(screen.getByText('Breakout')).toBeInTheDocument();
  });

  it('each family has a distinct label', () => {
    const families = ALL_SEVEN_STRATEGIES.map((s) => s.family);
    const uniqueFamilies = new Set(families);

    // 5 distinct families across 7 strategies
    expect(uniqueFamilies.size).toBe(5);
    expect(uniqueFamilies).toContain('orb_family');
    expect(uniqueFamilies).toContain('momentum');
    expect(uniqueFamilies).toContain('reversal');
    expect(uniqueFamilies).toContain('continuation');
    expect(uniqueFamilies).toContain('breakout');
  });

  it('displays operating window on new strategy card', () => {
    const r2g = ALL_SEVEN_STRATEGIES.find((s) => s.strategy_id === 'red_to_green')!;

    render(<PatternCard strategy={r2g} isSelected={false} onSelect={vi.fn()} />);

    expect(screen.getByText('9:45 – 11:00 AM')).toBeInTheDocument();
  });
});

describe('PatternCardGrid — 7 strategies', () => {
  it('renders all 7 cards', () => {
    render(
      <PatternCardGrid
        strategies={ALL_SEVEN_STRATEGIES}
        selectedId={null}
        onSelect={vi.fn()}
      />
    );

    expect(screen.getByText('ORB Breakout')).toBeInTheDocument();
    expect(screen.getByText('ORB Scalp')).toBeInTheDocument();
    expect(screen.getByText('VWAP Reclaim')).toBeInTheDocument();
    expect(screen.getByText('Afternoon Momentum')).toBeInTheDocument();
    expect(screen.getByText('Red-to-Green')).toBeInTheDocument();
    expect(screen.getByText('Bull Flag')).toBeInTheDocument();
    expect(screen.getByText('Flat-Top Breakout')).toBeInTheDocument();
  });
});

describe('IncubatorPipeline — new strategy counts', () => {
  it('counts exploration=3 for new strategies', () => {
    render(
      <IncubatorPipeline
        strategies={ALL_SEVEN_STRATEGIES}
        activeStageFilter={null}
        onStageClick={vi.fn()}
      />
    );

    // exploration stage should show count of 3 (R2G, Bull Flag, Flat-Top)
    const exploreButton = screen.getByRole('button', { name: /Explore.*\(3\)/ });
    expect(exploreButton).toBeInTheDocument();

    // paper_trading should show count of 4
    const paperButton = screen.getByRole('button', { name: /Paper.*\(4\)/ });
    expect(paperButton).toBeInTheDocument();
  });
});

describe('PatternCard — detail panel selection', () => {
  it('clicking new strategy card calls onSelect with correct ID', () => {
    const handleSelect = vi.fn();
    const r2g = ALL_SEVEN_STRATEGIES.find((s) => s.strategy_id === 'red_to_green')!;

    render(<PatternCard strategy={r2g} isSelected={false} onSelect={handleSelect} />);

    const cardContent = screen.getByText('Red-to-Green').closest('div');
    if (cardContent) {
      fireEvent.click(cardContent);
    }

    expect(handleSelect).toHaveBeenCalledWith('red_to_green');
  });
});
