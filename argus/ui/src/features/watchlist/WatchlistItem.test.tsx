/**
 * Tests for WatchlistItem component.
 *
 * Sprint 19, Session 12 — Updated for v3 layout:
 * - Removed sparklines from display (component still exists)
 * - Compact single-letter strategy badges
 * - VWAP distance display with arrows
 * - Short state labels (Above, Below, Entered)
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WatchlistItem, MiniSparkline } from './WatchlistItem';
import { CompactStrategyBadge } from '../../components/Badge';
import type { WatchlistItem as WatchlistItemType } from '../../api/types';

// Mock watchlist item data with VWAP tracking
const mockItem: WatchlistItemType = {
  symbol: 'TSLA',
  current_price: 250.50,
  gap_pct: 5.2,
  strategies: ['orb_breakout', 'vwap_reclaim'],
  vwap_state: 'above_vwap',
  sparkline: [
    { timestamp: '2026-02-26T14:30:00Z', price: 248.00 },
    { timestamp: '2026-02-26T14:31:00Z', price: 249.00 },
    { timestamp: '2026-02-26T14:32:00Z', price: 250.50 },
  ],
  vwap_distance_pct: 0.0045, // 0.45% above VWAP
};

describe('WatchlistItem', () => {
  it('renders symbol and price', () => {
    render(<WatchlistItem item={mockItem} />);

    expect(screen.getByText('TSLA')).toBeInTheDocument();
    // formatPrice returns price without $ prefix
    expect(screen.getByText('250.50')).toBeInTheDocument();
  });

  it('renders gap badge with correct styling for positive gap', () => {
    render(<WatchlistItem item={mockItem} />);

    const gapBadge = screen.getByText('+5.2%');
    expect(gapBadge).toBeInTheDocument();
    // Positive gap should have profit styling
    expect(gapBadge).toHaveClass('text-argus-profit');
  });

  it('renders gap badge with correct styling for negative gap', () => {
    const negativeItem: WatchlistItemType = {
      ...mockItem,
      gap_pct: -3.5,
    };
    render(<WatchlistItem item={negativeItem} />);

    const gapBadge = screen.getByText('-3.5%');
    expect(gapBadge).toBeInTheDocument();
    // Negative gap should have loss styling
    expect(gapBadge).toHaveClass('text-argus-loss');
  });

  it('renders compact strategy badges', () => {
    render(<WatchlistItem item={mockItem} />);

    // Should render compact badges (single letters with titles)
    // ORB shows as "O", VWAP shows as "V"
    expect(screen.getByTitle('ORB')).toBeInTheDocument();
    expect(screen.getByTitle('VWAP')).toBeInTheDocument();
  });

  it('shows VWAP state label for above_vwap state', () => {
    render(<WatchlistItem item={mockItem} />);

    // Short label "Above" should be visible
    expect(screen.getByText('Above')).toBeInTheDocument();
  });

  it('shows VWAP state label for below_vwap state', () => {
    const belowItem: WatchlistItemType = {
      ...mockItem,
      vwap_state: 'below_vwap',
      vwap_distance_pct: -0.0055,
    };
    render(<WatchlistItem item={belowItem} />);

    expect(screen.getByText('Below')).toBeInTheDocument();
  });

  it('shows VWAP state label for entered state', () => {
    const enteredItem: WatchlistItemType = {
      ...mockItem,
      vwap_state: 'entered',
      vwap_distance_pct: 0.0032,
    };
    render(<WatchlistItem item={enteredItem} />);

    expect(screen.getByText('Entered')).toBeInTheDocument();
  });

  it('does not show VWAP state for watching state', () => {
    const watchingItem: WatchlistItemType = {
      ...mockItem,
      vwap_state: 'watching',
      vwap_distance_pct: null,
    };
    render(<WatchlistItem item={watchingItem} />);

    // "Watching" label should not appear (show: false in config)
    expect(screen.queryByText('Watching')).not.toBeInTheDocument();
  });

  it('shows VWAP distance with up arrow for positive distance', () => {
    render(<WatchlistItem item={mockItem} />);

    // 0.0045 = 0.45% → "0.4%"
    // Check that up arrow exists
    expect(screen.getByText('↑', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('0.4%', { exact: false })).toBeInTheDocument();
  });

  it('shows VWAP distance with down arrow for negative distance', () => {
    const belowItem: WatchlistItemType = {
      ...mockItem,
      vwap_state: 'below_vwap',
      vwap_distance_pct: -0.0055,
    };
    render(<WatchlistItem item={belowItem} />);

    // -0.0055 = -0.55% → "0.5%" (JS floating point: 0.55.toFixed(1) = "0.5")
    expect(screen.getByText('↓', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('0.5%', { exact: false })).toBeInTheDocument();
  });

  it('does not show VWAP distance when null', () => {
    const noDistanceItem: WatchlistItemType = {
      ...mockItem,
      vwap_state: 'watching',
      vwap_distance_pct: null,
    };
    render(<WatchlistItem item={noDistanceItem} />);

    // No arrows should appear
    expect(screen.queryByText(/↑/)).not.toBeInTheDocument();
    expect(screen.queryByText(/↓/)).not.toBeInTheDocument();
  });

  it('shows left border accent for entered state', () => {
    const enteredItem: WatchlistItemType = {
      ...mockItem,
      vwap_state: 'entered',
      vwap_distance_pct: 0.0032,
    };
    render(<WatchlistItem item={enteredItem} />);

    const container = screen.getByRole('button');
    expect(container).toHaveClass('border-l-[3px]');
    expect(container).toHaveClass('border-l-argus-profit');
  });

  it('has transparent left border for non-entered states (alignment)', () => {
    render(<WatchlistItem item={mockItem} />);

    const container = screen.getByRole('button');
    // All items have the border width for alignment, but non-entered are transparent
    expect(container).toHaveClass('border-l-[3px]');
    expect(container).toHaveClass('border-l-transparent');
    expect(container).not.toHaveClass('border-l-argus-profit');
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<WatchlistItem item={mockItem} onClick={handleClick} />);

    const container = screen.getByRole('button');
    fireEvent.click(container);

    expect(handleClick).toHaveBeenCalledWith('TSLA');
  });

  it('calls onClick when Enter key is pressed', () => {
    const handleClick = vi.fn();
    render(<WatchlistItem item={mockItem} onClick={handleClick} />);

    const container = screen.getByRole('button');
    fireEvent.keyDown(container, { key: 'Enter' });

    expect(handleClick).toHaveBeenCalledWith('TSLA');
  });

  it('does not show VWAP indicator when vwap_reclaim not in strategies', () => {
    const nonVwapItem: WatchlistItemType = {
      ...mockItem,
      strategies: ['orb_breakout'],
      vwap_distance_pct: null,
    };
    render(<WatchlistItem item={nonVwapItem} />);

    // Should not have VWAP state indicator
    expect(screen.queryByText('Above')).not.toBeInTheDocument();
    expect(screen.queryByText('Below')).not.toBeInTheDocument();
    expect(screen.queryByText('Entered')).not.toBeInTheDocument();
  });
});

describe('CompactStrategyBadge', () => {
  it('renders single letter for ORB strategy', () => {
    render(<CompactStrategyBadge strategyId="orb_breakout" />);

    const badge = screen.getByTitle('ORB');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('O');
  });

  it('renders single letter for Scalp strategy', () => {
    render(<CompactStrategyBadge strategyId="orb_scalp" />);

    const badge = screen.getByTitle('SCALP');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('S');
  });

  it('renders single letter for VWAP strategy', () => {
    render(<CompactStrategyBadge strategyId="vwap_reclaim" />);

    const badge = screen.getByTitle('VWAP');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('V');
  });

  it('renders single letter for Momentum strategy', () => {
    render(<CompactStrategyBadge strategyId="afternoon_momentum" />);

    const badge = screen.getByTitle('MOM');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('A');
  });

  it('has correct compact sizing', () => {
    render(<CompactStrategyBadge strategyId="orb" />);

    const badge = screen.getByTitle('ORB');
    expect(badge).toHaveClass('w-5');
    expect(badge).toHaveClass('h-[18px]');
    expect(badge).toHaveClass('rounded-full');
  });
});

describe('MiniSparkline', () => {
  // MiniSparkline is still exported but not used in watchlist display
  // Keep tests for future use (detail panel, etc.)

  it('renders SVG polyline for valid data', () => {
    const data = [100, 105, 102, 108, 110];
    const { container } = render(<MiniSparkline data={data} />);

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();

    const polyline = container.querySelector('polyline');
    expect(polyline).toBeInTheDocument();
  });

  it('renders empty div for insufficient data', () => {
    const data = [100]; // Only one point
    const { container } = render(<MiniSparkline data={data} />);

    const svg = container.querySelector('svg');
    expect(svg).not.toBeInTheDocument();
  });

  it('uses green stroke for uptrend', () => {
    const data = [100, 102, 105, 108, 110]; // Uptrend
    const { container } = render(<MiniSparkline data={data} />);

    const polyline = container.querySelector('polyline');
    expect(polyline).toHaveAttribute('stroke', 'var(--color-argus-profit)');
  });

  it('uses red stroke for downtrend', () => {
    const data = [110, 108, 105, 102, 100]; // Downtrend
    const { container } = render(<MiniSparkline data={data} />);

    const polyline = container.querySelector('polyline');
    expect(polyline).toHaveAttribute('stroke', 'var(--color-argus-loss)');
  });

  it('has reduced opacity for subtle visual weight', () => {
    const data = [100, 105, 110];
    const { container } = render(<MiniSparkline data={data} />);

    const svg = container.querySelector('svg');
    expect(svg).toHaveStyle({ opacity: '0.7' });
  });
});
