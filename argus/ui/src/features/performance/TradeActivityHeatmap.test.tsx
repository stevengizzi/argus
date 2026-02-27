/**
 * TradeActivityHeatmap component tests.
 *
 * Sprint 21d Session 6: Trade activity heatmap visualization.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { TradeActivityHeatmap } from './TradeActivityHeatmap';

// Mock react-router-dom useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock the useHeatmapData hook
vi.mock('../../hooks/useHeatmapData', () => ({
  useHeatmapData: vi.fn(),
}));

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
  scaleSequential: vi.fn(() => {
    const scale = () => 'rgb(150, 150, 150)';
    scale.domain = vi.fn(() => scale);
    return scale;
  }),
}));

vi.mock('d3-scale-chromatic', () => ({
  interpolateRdYlGn: vi.fn((t: number) => `rgb(${Math.round(255 * t)}, ${Math.round(255 * (1 - t))}, 0)`),
}));

// Mock framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    motion: {
      div: ({
        children,
        ...props
      }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
    },
  };
});

import { useHeatmapData } from '../../hooks/useHeatmapData';

const mockHeatmapData = {
  cells: [
    { hour: 9, day_of_week: 0, trade_count: 5, avg_r_multiple: 1.2, net_pnl: 450 },
    { hour: 10, day_of_week: 1, trade_count: 3, avg_r_multiple: -0.5, net_pnl: -150 },
    { hour: 11, day_of_week: 2, trade_count: 8, avg_r_multiple: 0.8, net_pnl: 320 },
    { hour: 14, day_of_week: 4, trade_count: 2, avg_r_multiple: 2.0, net_pnl: 600 },
  ],
  period: 'month',
  timestamp: '2026-02-28T12:00:00Z',
};

function renderWithRouter(component: React.ReactElement) {
  return render(<BrowserRouter>{component}</BrowserRouter>);
}

describe('TradeActivityHeatmap', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  it('renders grid cells with data', () => {
    vi.mocked(useHeatmapData).mockReturnValue({
      data: mockHeatmapData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useHeatmapData>);

    renderWithRouter(<TradeActivityHeatmap period="month" />);

    // Should show the title
    expect(screen.getByText('Trade Activity Heatmap')).toBeInTheDocument();

    // Should show the color mode toggle
    expect(screen.getByText('By R-Multiple')).toBeInTheDocument();
    expect(screen.getByText('By P&L')).toBeInTheDocument();

    // Should render the SVG grid
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Should show day labels
    expect(screen.getByText('Mon')).toBeInTheDocument();
    expect(screen.getByText('Fri')).toBeInTheDocument();

    // Should show time labels
    expect(screen.getByText('9:30')).toBeInTheDocument();
    expect(screen.getByText('15:30')).toBeInTheDocument();

    // Should show trade counts in cells
    expect(screen.getByText('5')).toBeInTheDocument(); // 5 trades on Monday 9:30
    expect(screen.getByText('3')).toBeInTheDocument(); // 3 trades on Tuesday 10:00
  });

  it('handles empty data with message', () => {
    vi.mocked(useHeatmapData).mockReturnValue({
      data: { cells: [], period: 'month', timestamp: '2026-02-28T12:00:00Z' },
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useHeatmapData>);

    renderWithRouter(<TradeActivityHeatmap period="month" />);

    expect(screen.getByText('No trades in this period')).toBeInTheDocument();
  });

  it('applies color scale correctly', () => {
    vi.mocked(useHeatmapData).mockReturnValue({
      data: mockHeatmapData,
      isLoading: false,
      error: null,
      isFetching: false,
    } as ReturnType<typeof useHeatmapData>);

    const { container } = renderWithRouter(<TradeActivityHeatmap period="month" />);

    // Should have cells with different fill colors
    const cells = container.querySelectorAll('svg rect');
    expect(cells.length).toBeGreaterThan(0);

    // Should show the color legend
    expect(screen.getByText('Loss')).toBeInTheDocument();
    expect(screen.getByText('Profit')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    vi.mocked(useHeatmapData).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isFetching: true,
    } as ReturnType<typeof useHeatmapData>);

    renderWithRouter(<TradeActivityHeatmap period="month" />);

    expect(screen.getByText('Loading heatmap data...')).toBeInTheDocument();
  });

  it('shows error state', () => {
    vi.mocked(useHeatmapData).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to fetch'),
      isFetching: false,
    } as ReturnType<typeof useHeatmapData>);

    renderWithRouter(<TradeActivityHeatmap period="month" />);

    expect(screen.getByText('Failed to load heatmap data')).toBeInTheDocument();
  });
});
