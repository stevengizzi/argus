/**
 * CalendarPnlView component tests.
 *
 * Sprint 21d Session 6: Calendar P&L visualization.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { CalendarPnlView } from './CalendarPnlView';

// Mock react-router-dom useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock D3 scale functions
vi.mock('d3-scale', () => ({
  scaleDiverging: vi.fn(() => {
    const scale = (value: number) => {
      // Return a color based on value (simplified for testing)
      if (value > 0) return 'rgb(100, 200, 100)';
      if (value < 0) return 'rgb(200, 100, 100)';
      return 'rgb(255, 255, 255)';
    };
    scale.domain = vi.fn(() => scale);
    return scale;
  }),
}));

vi.mock('d3-scale-chromatic', () => ({
  interpolateRdYlGn: vi.fn((t: number) => `rgb(${Math.round(255 * t)}, ${Math.round(255 * (1 - t))}, 0)`),
}));

const mockDailyPnl = [
  { date: '2026-02-02', pnl: 150, trades: 3 },
  { date: '2026-02-03', pnl: -75, trades: 2 },
  { date: '2026-02-04', pnl: 220, trades: 5 },
  { date: '2026-02-05', pnl: 80, trades: 2 },
  { date: '2026-02-06', pnl: -30, trades: 1 },
  { date: '2026-02-09', pnl: 300, trades: 4 },
  { date: '2026-02-10', pnl: -120, trades: 3 },
  { date: '2026-02-24', pnl: 450, trades: 6 },
  { date: '2026-02-25', pnl: 200, trades: 4 },
  { date: '2026-02-26', pnl: -50, trades: 2 },
  { date: '2026-02-27', pnl: 175, trades: 3 },
];

function renderWithRouter(component: React.ReactElement) {
  return render(<BrowserRouter>{component}</BrowserRouter>);
}

describe('CalendarPnlView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  it('renders month grid with correct structure', () => {
    renderWithRouter(<CalendarPnlView dailyPnl={mockDailyPnl} />);

    // Should show the title
    expect(screen.getByText('Calendar P&L')).toBeInTheDocument();

    // Should show day headers
    expect(screen.getByText('Sun')).toBeInTheDocument();
    expect(screen.getByText('Mon')).toBeInTheDocument();
    expect(screen.getByText('Tue')).toBeInTheDocument();
    expect(screen.getByText('Wed')).toBeInTheDocument();
    expect(screen.getByText('Thu')).toBeInTheDocument();
    expect(screen.getByText('Fri')).toBeInTheDocument();
    expect(screen.getByText('Sat')).toBeInTheDocument();

    // Should show month/year
    expect(screen.getByText('February 2026')).toBeInTheDocument();

    // Should have navigation arrows
    expect(screen.getByLabelText('Previous month')).toBeInTheDocument();
    expect(screen.getByLabelText('Next month')).toBeInTheDocument();
  });

  it('shows correct day positions in calendar', () => {
    renderWithRouter(<CalendarPnlView dailyPnl={mockDailyPnl} />);

    // Feb 2026 starts on Sunday, so 1st should be in first column
    // Check that we have date numbers displayed
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('28')).toBeInTheDocument(); // Feb 2026 has 28 days

    // Check P&L values are shown
    expect(screen.getByText('+$150')).toBeInTheDocument();
    expect(screen.getByText('-$75')).toBeInTheDocument();
    expect(screen.getByText('+$450')).toBeInTheDocument();
  });

  it('applies P&L colors correctly', () => {
    const { container } = renderWithRouter(<CalendarPnlView dailyPnl={mockDailyPnl} />);

    // Days with P&L should have colored backgrounds
    const dayCells = container.querySelectorAll('.min-h-\\[52px\\]');
    expect(dayCells.length).toBeGreaterThan(0);

    // Check that some cells have background colors (from D3 scale)
    const cellsWithBg = Array.from(dayCells).filter((cell) => {
      const style = cell.getAttribute('style');
      return style && style.includes('background-color') && !style.includes('transparent');
    });
    expect(cellsWithBg.length).toBeGreaterThan(0);
  });

  it('shows weekly totals', () => {
    renderWithRouter(<CalendarPnlView dailyPnl={mockDailyPnl} />);

    // Should show week labels
    expect(screen.getByText(/Week 1:/)).toBeInTheDocument();
    expect(screen.getByText(/Week 2:/)).toBeInTheDocument();
  });

  it('navigates months with arrows', () => {
    renderWithRouter(<CalendarPnlView dailyPnl={mockDailyPnl} />);

    // Initially showing February 2026
    expect(screen.getByText('February 2026')).toBeInTheDocument();

    // Click previous month
    fireEvent.click(screen.getByLabelText('Previous month'));
    expect(screen.getByText('January 2026')).toBeInTheDocument();

    // Click next month twice to get to March
    fireEvent.click(screen.getByLabelText('Next month'));
    fireEvent.click(screen.getByLabelText('Next month'));
    expect(screen.getByText('March 2026')).toBeInTheDocument();
  });

  it('handles empty data', () => {
    renderWithRouter(<CalendarPnlView dailyPnl={[]} />);

    expect(screen.getByText('No P&L data available')).toBeInTheDocument();
  });
});
