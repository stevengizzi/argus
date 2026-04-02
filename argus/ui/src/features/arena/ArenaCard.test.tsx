/**
 * Tests for ArenaCard component and computeProgressPct helper.
 *
 * Sprint 32.75, Session 9.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ArenaCard, computeProgressPct } from './ArenaCard';
import type { CandleData } from './MiniChart';

// Mock MiniChart to avoid LWC canvas dependency in ArenaCard tests.
vi.mock('./MiniChart', () => ({
  MiniChart: vi.fn(() => <div data-testid="mini-chart-container" />),
}));

// --- Fixtures ---

const SAMPLE_CANDLES: CandleData[] = [
  { time: 1700000000 as CandleData['time'], open: 150, high: 152, low: 149, close: 151 },
  { time: 1700000060 as CandleData['time'], open: 151, high: 153, low: 150, close: 152 },
];

const DEFAULT_PROPS = {
  symbol: 'NVDA',
  strategy_id: 'strat_orb_breakout',
  pnl: 125.50,
  r_multiple: 0.85,
  hold_seconds: 180,
  entry_price: 500,
  stop_price: 490,
  target_prices: [510, 520],
  candles: SAMPLE_CANDLES,
};

describe('ArenaCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the symbol label', () => {
    render(<ArenaCard {...DEFAULT_PROPS} />);
    expect(screen.getByTestId('symbol-label')).toHaveTextContent('NVDA');
  });

  it('renders the strategy badge with short name', () => {
    render(<ArenaCard {...DEFAULT_PROPS} />);
    expect(screen.getByTestId('strategy-badge')).toBeInTheDocument();
    expect(screen.getByTestId('strategy-badge')).toHaveTextContent('ORB');
  });

  it('renders the MiniChart component', () => {
    render(<ArenaCard {...DEFAULT_PROPS} />);
    expect(screen.getByTestId('mini-chart-container')).toBeInTheDocument();
  });

  it('renders the hold timer', () => {
    render(<ArenaCard {...DEFAULT_PROPS} hold_seconds={125} />);
    expect(screen.getByTestId('hold-timer')).toHaveTextContent('02:05');
  });

  it('renders the progress bar track and indicator', () => {
    render(<ArenaCard {...DEFAULT_PROPS} />);
    expect(screen.getByTestId('progress-bar-track')).toBeInTheDocument();
    expect(screen.getByTestId('progress-bar-indicator')).toBeInTheDocument();
  });

  it('renders the arena card container', () => {
    render(<ArenaCard {...DEFAULT_PROPS} />);
    expect(screen.getByTestId('arena-card')).toBeInTheDocument();
  });

  it('arena card container has no inline border style', () => {
    render(<ArenaCard {...DEFAULT_PROPS} />);
    const card = screen.getByTestId('arena-card');
    expect(card.getAttribute('style')).toBeNull();
  });

  it('progress bar area shows Stop and T1 labels', () => {
    render(<ArenaCard {...DEFAULT_PROPS} />);
    expect(screen.getByTestId('progress-label-stop')).toHaveTextContent('Stop');
    expect(screen.getByTestId('progress-label-t1')).toHaveTextContent('T1');
  });

  describe('P&L formatting', () => {
    it('formats positive P&L with green color class and + prefix', () => {
      render(<ArenaCard {...DEFAULT_PROPS} pnl={125.50} />);
      const pnlEl = screen.getByTestId('pnl-label');
      expect(pnlEl).toHaveTextContent('+$125.50');
      expect(pnlEl.className).toMatch(/green/);
    });

    it('formats negative P&L with red color class and - prefix', () => {
      render(<ArenaCard {...DEFAULT_PROPS} pnl={-87.25} r_multiple={-0.87} />);
      const pnlEl = screen.getByTestId('pnl-label');
      expect(pnlEl).toHaveTextContent('-$87.25');
      expect(pnlEl.className).toMatch(/red/);
    });

    it('formats zero P&L as positive', () => {
      render(<ArenaCard {...DEFAULT_PROPS} pnl={0} r_multiple={0} />);
      const pnlEl = screen.getByTestId('pnl-label');
      expect(pnlEl).toHaveTextContent('+$0.00');
    });
  });

  describe('R-multiple display', () => {
    it('shows + prefix on positive R', () => {
      render(<ArenaCard {...DEFAULT_PROPS} r_multiple={1.5} />);
      expect(screen.getByTestId('r-multiple-label')).toHaveTextContent('+1.50R');
    });

    it('shows negative R without + prefix', () => {
      render(<ArenaCard {...DEFAULT_PROPS} pnl={-50} r_multiple={-0.5} />);
      expect(screen.getByTestId('r-multiple-label')).toHaveTextContent('-0.50R');
    });
  });

  describe('hold timer formatting', () => {
    it('formats seconds-only duration as MM:SS', () => {
      render(<ArenaCard {...DEFAULT_PROPS} hold_seconds={45} />);
      expect(screen.getByTestId('hold-timer')).toHaveTextContent('00:45');
    });

    it('formats hour-long duration as H:MM:SS', () => {
      render(<ArenaCard {...DEFAULT_PROPS} hold_seconds={3723} />);
      expect(screen.getByTestId('hold-timer')).toHaveTextContent('1:02:03');
    });
  });
});

describe('computeProgressPct', () => {
  it('returns 0 when price is at stop', () => {
    expect(computeProgressPct(490, 490, 510)).toBe(0);
  });

  it('returns 100 when price is at T1', () => {
    expect(computeProgressPct(510, 490, 510)).toBe(100);
  });

  it('returns 50 when price is midway between stop and T1', () => {
    expect(computeProgressPct(500, 490, 510)).toBe(50);
  });

  it('clamps to 0 when price is below stop', () => {
    expect(computeProgressPct(485, 490, 510)).toBe(0);
  });

  it('clamps to 100 when price is above T1', () => {
    expect(computeProgressPct(520, 490, 510)).toBe(100);
  });

  it('returns 0 when stop equals T1 (degenerate range)', () => {
    expect(computeProgressPct(500, 500, 500)).toBe(0);
  });
});
