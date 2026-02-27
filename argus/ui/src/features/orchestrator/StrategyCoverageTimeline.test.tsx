/**
 * Tests for StrategyCoverageTimeline component.
 *
 * Sprint 21b, Session 8.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StrategyCoverageTimeline } from './StrategyCoverageTimeline';
import type { AllocationInfo } from '../../api/types';

// Mock useMediaQuery hook
vi.mock('../../hooks/useMediaQuery', () => ({
  useMediaQuery: vi.fn(() => true), // Default to desktop
}));

// Mock allocations with operating windows
const mockAllocations: AllocationInfo[] = [
  {
    strategy_id: 'orb_breakout',
    allocation_pct: 25,
    allocation_dollars: 10000,
    throttle_action: 'none',
    eligible: true,
    reason: '',
    deployed_capital: 5000,
    deployed_pct: 12.5,
    is_throttled: false,
    operating_window: {
      earliest_entry: '09:35',
      latest_entry: '10:05',
      force_close: '10:30',
    },
    consecutive_losses: 0,
    rolling_sharpe: 1.5,
    drawdown_pct: 2.0,
    is_active: true,
    health_status: 'healthy',
    trade_count_today: 2,
    daily_pnl: 150,
    open_position_count: 1,
    override_active: false,
    override_until: null,
  },
  {
    strategy_id: 'vwap_reclaim',
    allocation_pct: 25,
    allocation_dollars: 10000,
    throttle_action: 'reduce',
    eligible: true,
    reason: 'Consecutive losses',
    deployed_capital: 3000,
    deployed_pct: 7.5,
    is_throttled: true,
    operating_window: {
      earliest_entry: '10:00',
      latest_entry: '14:00',
      force_close: '15:30',
    },
    consecutive_losses: 3,
    rolling_sharpe: -0.5,
    drawdown_pct: 8.0,
    is_active: true,
    health_status: 'warning',
    trade_count_today: 1,
    daily_pnl: -75,
    open_position_count: 0,
    override_active: false,
    override_until: null,
  },
];

describe('StrategyCoverageTimeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders SVG element with strategy bars', () => {
    render(<StrategyCoverageTimeline allocations={mockAllocations} />);

    // Check for SVG element
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Check for strategy bars (rect elements)
    const rects = svg?.querySelectorAll('rect');
    // Should have at least 2 rects (one per strategy with operating window)
    expect(rects?.length).toBeGreaterThanOrEqual(2);
  });

  it('throttled strategy bar has reduced opacity', () => {
    render(<StrategyCoverageTimeline allocations={mockAllocations} />);

    const svg = document.querySelector('svg');
    const rects = svg?.querySelectorAll('rect');

    // Find the main bars (not the stripe overlays)
    const mainBars = Array.from(rects || []).filter(
      (rect) => rect.getAttribute('fill')?.startsWith('#')
    );

    // Check that at least one bar has reduced opacity (throttled)
    const hasThrottledBar = mainBars.some(
      (rect) => parseFloat(rect.getAttribute('opacity') || '1') < 0.5
    );
    expect(hasThrottledBar).toBe(true);

    // Check that at least one bar has normal opacity (not throttled)
    const hasNormalBar = mainBars.some(
      (rect) => parseFloat(rect.getAttribute('opacity') || '0') >= 0.5
    );
    expect(hasNormalBar).toBe(true);
  });
});
