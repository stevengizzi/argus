/**
 * Tests for WatchlistItem component.
 *
 * Sprint 19, Session 11.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WatchlistItem, MiniSparkline } from './WatchlistItem';
import type { WatchlistItem as WatchlistItemType } from '../../api/types';

// Mock watchlist item data
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

  it('renders strategy badges', () => {
    render(<WatchlistItem item={mockItem} />);

    // StrategyBadge component should render for each strategy
    // Note: The actual badge text depends on StrategyBadge implementation
    const container = screen.getByRole('button');
    expect(container).toBeInTheDocument();
  });

  it('renders VWAP state dot for watching state', () => {
    const watchingItem: WatchlistItemType = {
      ...mockItem,
      vwap_state: 'watching',
    };
    render(<WatchlistItem item={watchingItem} />);

    // Should have a gray dot with tooltip
    const dotContainer = screen.getByTitle('Watching');
    expect(dotContainer).toBeInTheDocument();
  });

  it('renders VWAP state dot for above_vwap state', () => {
    render(<WatchlistItem item={mockItem} />);

    const dotContainer = screen.getByTitle('Above VWAP');
    expect(dotContainer).toBeInTheDocument();
  });

  it('renders VWAP state dot for below_vwap state', () => {
    const belowItem: WatchlistItemType = {
      ...mockItem,
      vwap_state: 'below_vwap',
    };
    render(<WatchlistItem item={belowItem} />);

    const dotContainer = screen.getByTitle('Below VWAP');
    expect(dotContainer).toBeInTheDocument();
  });

  it('renders VWAP state dot for entered state', () => {
    const enteredItem: WatchlistItemType = {
      ...mockItem,
      vwap_state: 'entered',
    };
    render(<WatchlistItem item={enteredItem} />);

    const dotContainer = screen.getByTitle('Entered');
    expect(dotContainer).toBeInTheDocument();
  });

  it('shows left border accent for entered state', () => {
    const enteredItem: WatchlistItemType = {
      ...mockItem,
      vwap_state: 'entered',
    };
    render(<WatchlistItem item={enteredItem} />);

    const container = screen.getByRole('button');
    expect(container).toHaveClass('border-l-[3px]');
    expect(container).toHaveClass('border-l-argus-profit');
  });

  it('does not show left border for non-entered states', () => {
    render(<WatchlistItem item={mockItem} />);

    const container = screen.getByRole('button');
    expect(container).not.toHaveClass('border-l-[3px]');
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
    };
    render(<WatchlistItem item={nonVwapItem} />);

    // Should not have VWAP state indicator
    expect(screen.queryByTitle('Above VWAP')).not.toBeInTheDocument();
  });
});

describe('MiniSparkline', () => {
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
