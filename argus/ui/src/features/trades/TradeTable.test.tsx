/**
 * Tests for TradeTable quality column integration.
 *
 * Sprint 24 Session 9.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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
