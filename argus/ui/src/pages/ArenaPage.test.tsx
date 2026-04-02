/**
 * Tests for ArenaPage shell — Sprint 32.75, Session 8.
 *
 * Covers: page renders, stats bar fields, controls dropdowns,
 * empty state, and nav registration.
 *
 * Updated S10: mock useArenaData so the page tests remain synchronous
 * and don't require a QueryClientProvider.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ArenaPage } from './ArenaPage';
import { ArenaStatsBar } from '../features/arena/ArenaStatsBar';
import { ArenaControls } from '../features/arena/ArenaControls';
import { Sidebar } from '../layouts/Sidebar';

vi.mock('../features/arena/useArenaWebSocket', () => ({
  useArenaWebSocket: vi.fn(() => ({
    positions: [],
    stats: { position_count: 0, total_pnl: 0, net_r: 0, entries_5m: 0, exits_5m: 0 },
    liveOverlays: {},
    wsStatus: 'disconnected' as const,
    registerChartRef: vi.fn(),
  })),
}));

vi.mock('../hooks/useArenaData', () => ({
  useArenaData: vi.fn(() => ({
    positions: [],
    candlesBySymbol: {},
    isLoading: false,
    error: null,
    stats: { position_count: 0, total_pnl: 0, net_r: 0 },
  })),
  sortPositions: vi.fn((positions: unknown[]) => positions),
  filterPositions: vi.fn((positions: unknown[]) => positions),
}));

function wrap(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

// ─── ArenaPage ───────────────────────────────────────────────────────────────

describe('ArenaPage', () => {
  it('renders without errors', () => {
    wrap(<ArenaPage />);
    expect(screen.getByTestId('arena-page')).toBeInTheDocument();
  });

  it('shows empty state when there are no positions', () => {
    wrap(<ArenaPage />);
    expect(screen.getByTestId('arena-empty-state')).toBeInTheDocument();
    expect(screen.getByText('No open positions')).toBeInTheDocument();
  });

  it('renders the stats bar inside the page', () => {
    wrap(<ArenaPage />);
    expect(screen.getByTestId('arena-stats-bar')).toBeInTheDocument();
  });

  it('renders the controls bar inside the page', () => {
    wrap(<ArenaPage />);
    expect(screen.getByTestId('arena-controls')).toBeInTheDocument();
  });
});

// ─── ArenaStatsBar ───────────────────────────────────────────────────────────

describe('ArenaStatsBar', () => {
  it('renders all five stat fields with default placeholders', () => {
    render(<ArenaStatsBar />);
    expect(screen.getByTestId('stat-position-count')).toBeInTheDocument();
    expect(screen.getByTestId('stat-total-pnl')).toBeInTheDocument();
    expect(screen.getByTestId('stat-net-r')).toBeInTheDocument();
    expect(screen.getByTestId('stat-entries-5m')).toBeInTheDocument();
    expect(screen.getByTestId('stat-exits-5m')).toBeInTheDocument();
  });

  it('displays positive P&L in profit color class', () => {
    render(<ArenaStatsBar totalPnl={250.5} />);
    const pnl = screen.getByTestId('stat-total-pnl');
    expect(pnl).toHaveClass('text-argus-profit');
    expect(pnl.textContent).toBe('+$250.50');
  });

  it('displays negative P&L in loss color class', () => {
    render(<ArenaStatsBar totalPnl={-120.75} />);
    const pnl = screen.getByTestId('stat-total-pnl');
    expect(pnl).toHaveClass('text-argus-loss');
    expect(pnl.textContent).toBe('-$120.75');
  });

  it('displays position count and entry/exit counts', () => {
    render(<ArenaStatsBar positionCount={7} entries5m={3} exits5m={1} />);
    expect(screen.getByTestId('stat-position-count').textContent).toBe('7');
    expect(screen.getByTestId('stat-entries-5m').textContent).toBe('3');
    expect(screen.getByTestId('stat-exits-5m').textContent).toBe('1');
  });
});

// ─── ArenaControls ───────────────────────────────────────────────────────────

describe('ArenaControls', () => {
  it('renders sort and strategy filter dropdowns', () => {
    const noop = () => undefined;
    render(
      <ArenaControls
        sortMode="entry_time"
        onSortChange={noop}
        strategyFilter="all"
        onFilterChange={noop}
      />,
    );
    expect(screen.getByTestId('sort-mode-select')).toBeInTheDocument();
    expect(screen.getByTestId('strategy-filter-select')).toBeInTheDocument();
  });

  it('sort dropdown lists all four sort modes', () => {
    const noop = () => undefined;
    render(
      <ArenaControls
        sortMode="entry_time"
        onSortChange={noop}
        strategyFilter="all"
        onFilterChange={noop}
      />,
    );
    const select = screen.getByTestId('sort-mode-select');
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.value);
    expect(options).toContain('entry_time');
    expect(options).toContain('strategy');
    expect(options).toContain('pnl');
    expect(options).toContain('urgency');
  });

  it('strategy filter includes "All" and at least the 12 known strategies', () => {
    const noop = () => undefined;
    render(
      <ArenaControls
        sortMode="entry_time"
        onSortChange={noop}
        strategyFilter="all"
        onFilterChange={noop}
      />,
    );
    const select = screen.getByTestId('strategy-filter-select');
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.value);
    expect(options).toContain('all');
    expect(options).toContain('strat_orb_breakout');
    expect(options).toContain('strat_premarket_high_break');
    expect(options.length).toBeGreaterThanOrEqual(13); // all + 12 strategies
  });

  it('calls onSortChange when sort dropdown changes', () => {
    let called = '';
    render(
      <ArenaControls
        sortMode="entry_time"
        onSortChange={(mode) => { called = mode; }}
        strategyFilter="all"
        onFilterChange={() => undefined}
      />,
    );
    fireEvent.change(screen.getByTestId('sort-mode-select'), { target: { value: 'pnl' } });
    expect(called).toBe('pnl');
  });

  it('calls onFilterChange when strategy dropdown changes', () => {
    let called = '';
    render(
      <ArenaControls
        sortMode="entry_time"
        onSortChange={() => undefined}
        strategyFilter="all"
        onFilterChange={(id) => { called = id; }}
      />,
    );
    fireEvent.change(screen.getByTestId('strategy-filter-select'), {
      target: { value: 'strat_bull_flag' },
    });
    expect(called).toBe('strat_bull_flag');
  });
});

// ─── Nav registration ────────────────────────────────────────────────────────

describe('Sidebar nav', () => {
  it('includes The Arena nav item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('The Arena')).toBeInTheDocument();
  });
});
