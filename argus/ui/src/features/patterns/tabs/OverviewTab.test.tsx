/**
 * Tests for OverviewTab component.
 *
 * Sprint 21a, Session 4.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { OverviewTab } from './OverviewTab';
import type { StrategyInfo } from '../../../api/types';

// Mock the useStrategySpec hook
vi.mock('../../../hooks/useStrategySpec', () => ({
  useStrategySpec: vi.fn(),
}));

// Import the mocked module to control its return values
import { useStrategySpec } from '../../../hooks/useStrategySpec';
const mockedUseStrategySpec = vi.mocked(useStrategySpec);

// Mock strategy with config data
const mockStrategy: StrategyInfo = {
  strategy_id: 'orb_breakout',
  name: 'ORB Breakout',
  version: '1.0.0',
  is_active: true,
  pipeline_stage: 'paper_trading',
  allocated_capital: 10000,
  daily_pnl: 150,
  trade_count_today: 3,
  open_positions: 1,
  config_summary: {
    orb_window_minutes: 5,
    target_1_r: 1.0,
    target_2_r: 2.0,
    time_stop_minutes: 15,
    enabled: true,
  },
  time_window: '9:30 AM – 10:00 AM',
  family: 'orb_family',
  description_short: 'Opening range breakout strategy',
  performance_summary: null,
  backtest_summary: null,
};

describe('OverviewTab', () => {
  it('renders parameter table with config data', () => {
    // Mock successful spec load
    mockedUseStrategySpec.mockReturnValue({
      data: {
        strategy_id: 'orb_breakout',
        content: '# Strategy Spec\n\nThis is the spec.',
        format: 'markdown',
      },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useStrategySpec>);

    render(<OverviewTab strategy={mockStrategy} />);

    // Section header
    expect(screen.getByText('Current Parameters')).toBeInTheDocument();

    // Parameter names (formatted)
    expect(screen.getByText('ORB Window (min)')).toBeInTheDocument();
    expect(screen.getByText('Target 1 (R)')).toBeInTheDocument();
    expect(screen.getByText('Target 2 (R)')).toBeInTheDocument();
    expect(screen.getByText('Time Stop (min)')).toBeInTheDocument();
    expect(screen.getByText('Enabled')).toBeInTheDocument();

    // Parameter values (1.0 and 2.0 are treated as integers in JS)
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();  // target_1_r: 1.0 → "1"
    expect(screen.getByText('2')).toBeInTheDocument();  // target_2_r: 2.0 → "2"
    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('Yes')).toBeInTheDocument();
  });

  it('shows loading state while fetching spec', () => {
    // Mock loading state
    mockedUseStrategySpec.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useStrategySpec>);

    render(<OverviewTab strategy={mockStrategy} />);

    // Documentation section header
    expect(screen.getByText('Strategy Documentation')).toBeInTheDocument();

    // Loading skeleton
    expect(screen.getByTestId('spec-loading')).toBeInTheDocument();
  });
});
