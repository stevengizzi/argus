/**
 * Tests for TradeTable quality column integration.
 *
 * Sprint 24 Session 9.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TradeTable } from './TradeTable';
import type { Trade } from '../../api/types';

// Mock Zustand store
vi.mock('../../stores/symbolDetailUI', () => ({
  useSymbolDetailUI: () => vi.fn(),
}));

const baseTrade: Trade = {
  id: 'test-001',
  strategy_id: 'orb_breakout',
  symbol: 'AAPL',
  side: 'long',
  entry_price: 150.0,
  entry_time: '2026-03-14T10:15:00Z',
  exit_price: 153.0,
  exit_time: '2026-03-14T11:30:00Z',
  shares: 100,
  pnl_dollars: 300.0,
  pnl_r_multiple: 1.5,
  exit_reason: 'target_1',
  hold_duration_seconds: 4500,
  commission: 1.0,
  market_regime: 'bullish',
  stop_price: 148.0,
  target_prices: [153.0, 156.0],
  quality_grade: null,
  quality_score: null,
};

describe('TradeTable quality column', () => {
  it('renders Quality column header', () => {
    render(
      <TradeTable
        trades={[baseTrade]}
        totalCount={1}
      />
    );

    expect(screen.getByText('Quality')).toBeInTheDocument();
  });

  it('shows dash for trade without quality grade', () => {
    render(
      <TradeTable
        trades={[baseTrade]}
        totalCount={1}
      />
    );

    // The quality cell should show "—" for null grade
    // There are multiple "—" in the table (exit price, duration, etc.)
    // but the Quality column's dash is in a md:table-cell td
    const cells = document.querySelectorAll('td.hidden.md\\:table-cell');
    const qualityCells = Array.from(cells).filter(
      (cell) => cell.textContent === '—' && cell.classList.contains('text-center')
    );
    expect(qualityCells.length).toBeGreaterThanOrEqual(1);
  });

  it('renders QualityBadge for trade with quality grade', () => {
    const tradeWithQuality: Trade = {
      ...baseTrade,
      quality_grade: 'A+',
      quality_score: 92.3,
    };

    render(
      <TradeTable
        trades={[tradeWithQuality]}
        totalCount={1}
      />
    );

    // The QualityBadge renders the grade text
    expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
    expect(screen.getByText('A+')).toBeInTheDocument();
  });

  it('handles empty string quality grade as no grade', () => {
    const tradeEmptyGrade: Trade = {
      ...baseTrade,
      quality_grade: '',
      quality_score: 0,
    };

    render(
      <TradeTable
        trades={[tradeEmptyGrade]}
        totalCount={1}
      />
    );

    // Empty string is falsy, so should show "—"
    const cells = document.querySelectorAll('td.hidden.md\\:table-cell');
    const qualityCells = Array.from(cells).filter(
      (cell) => cell.textContent === '—' && cell.classList.contains('text-center')
    );
    expect(qualityCells.length).toBeGreaterThanOrEqual(1);
  });
});

describe('TradeTable quality sort', () => {
  const trades: Trade[] = [
    { ...baseTrade, id: '1', symbol: 'AAPL', quality_grade: 'B+', quality_score: 70 },
    { ...baseTrade, id: '2', symbol: 'TSLA', quality_grade: 'A+', quality_score: 95 },
    { ...baseTrade, id: '3', symbol: 'NVDA', quality_grade: null, quality_score: null },
    { ...baseTrade, id: '4', symbol: 'MSFT', quality_grade: 'C', quality_score: 40 },
    { ...baseTrade, id: '5', symbol: 'GOOG', quality_grade: 'A-', quality_score: 82 },
  ];

  it('sorts by quality grade in ascending order (A+ first)', async () => {
    const user = userEvent.setup();
    render(<TradeTable trades={trades} totalCount={trades.length} />);

    const qualityHeader = screen.getByTestId('sort-quality');
    await user.click(qualityHeader);

    // After one click: ascending (A+ = index 0 first, then A-, B+, C, null last)
    const rows = document.querySelectorAll('tbody tr');
    const symbols = Array.from(rows).map(
      (row) => row.querySelectorAll('td')[2]?.textContent // desktop symbol column
    );

    expect(symbols).toEqual(['TSLA', 'GOOG', 'AAPL', 'MSFT', 'NVDA']);
  });

  it('sorts by quality grade in descending order (C first, null last)', async () => {
    const user = userEvent.setup();
    render(<TradeTable trades={trades} totalCount={trades.length} />);

    const qualityHeader = screen.getByTestId('sort-quality');
    await user.click(qualityHeader); // asc
    await user.click(qualityHeader); // desc

    const rows = document.querySelectorAll('tbody tr');
    const symbols = Array.from(rows).map(
      (row) => row.querySelectorAll('td')[2]?.textContent
    );

    // Descending: C first, then B+, A-, A+. Null still last.
    expect(symbols).toEqual(['MSFT', 'AAPL', 'GOOG', 'TSLA', 'NVDA']);
  });

  it('clears sort on third click', async () => {
    const user = userEvent.setup();
    render(<TradeTable trades={trades} totalCount={trades.length} />);

    const qualityHeader = screen.getByTestId('sort-quality');
    await user.click(qualityHeader); // asc
    await user.click(qualityHeader); // desc
    await user.click(qualityHeader); // clear

    // Back to original order
    const rows = document.querySelectorAll('tbody tr');
    const symbols = Array.from(rows).map(
      (row) => row.querySelectorAll('td')[2]?.textContent
    );

    expect(symbols).toEqual(['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOG']);
  });
});
