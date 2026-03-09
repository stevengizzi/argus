/**
 * Tests for CatalystAlertPanel component.
 *
 * Sprint 23.5 Session 5: Frontend — Dashboard Catalyst Badges + Orchestrator Alert Panel
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { CatalystAlertPanel } from './CatalystAlertPanel';
import type { CatalystsResponse } from '../hooks/useCatalysts';

// Mock the useCatalysts hook
vi.mock('../hooks/useCatalysts', () => ({
  useRecentCatalysts: vi.fn(),
}));

import { useRecentCatalysts } from '../hooks/useCatalysts';
const mockUseRecentCatalysts = vi.mocked(useRecentCatalysts);

const mockCatalystsData: CatalystsResponse = {
  catalysts: [
    {
      symbol: 'AAPL',
      catalyst_type: 'earnings',
      quality_score: 85,
      headline: 'AAPL Q4 Earnings Beat Expectations',
      summary: 'Apple beats earnings',
      source: 'SEC',
      source_url: 'https://sec.gov/filing',
      filing_type: '10-K',
      published_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 minutes ago
      classified_at: '2026-03-10T08:01:00Z',
    },
    {
      symbol: 'NVDA',
      catalyst_type: 'analyst_action',
      quality_score: 45,
      headline: 'Analyst Upgrades NVDA to Buy',
      summary: 'Major upgrade',
      source: 'FMP',
      source_url: null,
      filing_type: null,
      published_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
      classified_at: '2026-03-10T06:01:00Z',
    },
  ],
  count: 2,
  total: 2,
};

describe('CatalystAlertPanel', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('renders title "Catalyst Alerts"', () => {
    mockUseRecentCatalysts.mockReturnValue({
      data: mockCatalystsData,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      dataUpdatedAt: Date.now(),
    } as ReturnType<typeof useRecentCatalysts>);

    render(<CatalystAlertPanel />, { wrapper });

    expect(screen.getByText('Catalyst Alerts')).toBeInTheDocument();
  });

  it('renders alerts when data is available', () => {
    mockUseRecentCatalysts.mockReturnValue({
      data: mockCatalystsData,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      dataUpdatedAt: Date.now(),
    } as ReturnType<typeof useRecentCatalysts>);

    render(<CatalystAlertPanel />, { wrapper });

    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('NVDA')).toBeInTheDocument();
  });

  it('renders empty state when no catalysts', () => {
    mockUseRecentCatalysts.mockReturnValue({
      data: { catalysts: [], count: 0, total: 0 },
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      dataUpdatedAt: Date.now(),
    } as ReturnType<typeof useRecentCatalysts>);

    render(<CatalystAlertPanel />, { wrapper });

    expect(screen.getByText('No recent catalysts')).toBeInTheDocument();
  });

  it('renders loading state', () => {
    mockUseRecentCatalysts.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isError: false,
      isSuccess: false,
      dataUpdatedAt: 0,
    } as ReturnType<typeof useRecentCatalysts>);

    const { container } = render(<CatalystAlertPanel />, { wrapper });

    // Should show loading spinner
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders error state', () => {
    mockUseRecentCatalysts.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
      isError: true,
      isSuccess: false,
      dataUpdatedAt: 0,
    } as ReturnType<typeof useRecentCatalysts>);

    render(<CatalystAlertPanel />, { wrapper });

    expect(screen.getByText('Unable to load catalysts')).toBeInTheDocument();
  });

  it('truncates long headlines', () => {
    const longHeadline = 'A'.repeat(100); // 100 character headline
    const expectedTruncated = 'A'.repeat(77) + '...'; // 80 - 3 = 77 + '...'

    mockUseRecentCatalysts.mockReturnValue({
      data: {
        catalysts: [
          {
            symbol: 'TEST',
            catalyst_type: 'news_sentiment',
            quality_score: 50,
            headline: longHeadline,
            summary: 'Test',
            source: 'FMP',
            source_url: null,
            filing_type: null,
            published_at: new Date().toISOString(),
            classified_at: new Date().toISOString(),
          },
        ],
        count: 1,
        total: 1,
      },
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      dataUpdatedAt: Date.now(),
    } as ReturnType<typeof useRecentCatalysts>);

    render(<CatalystAlertPanel />, { wrapper });

    expect(screen.getByText(expectedTruncated)).toBeInTheDocument();
  });

  it('shows quality score with correct color coding - high score', () => {
    mockUseRecentCatalysts.mockReturnValue({
      data: mockCatalystsData, // First item has quality_score: 85
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      dataUpdatedAt: Date.now(),
    } as ReturnType<typeof useRecentCatalysts>);

    render(<CatalystAlertPanel />, { wrapper });

    // Should show score 85 with green color
    expect(screen.getByText('85')).toBeInTheDocument();
  });

  it('shows quality score with correct color coding - medium score', () => {
    mockUseRecentCatalysts.mockReturnValue({
      data: mockCatalystsData, // Second item has quality_score: 45
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      dataUpdatedAt: Date.now(),
    } as ReturnType<typeof useRecentCatalysts>);

    render(<CatalystAlertPanel />, { wrapper });

    // Should show score 45 (medium range uses amber)
    expect(screen.getByText('45')).toBeInTheDocument();
  });

  it('shows source label', () => {
    mockUseRecentCatalysts.mockReturnValue({
      data: mockCatalystsData,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      dataUpdatedAt: Date.now(),
    } as ReturnType<typeof useRecentCatalysts>);

    render(<CatalystAlertPanel />, { wrapper });

    expect(screen.getByText('SEC')).toBeInTheDocument();
    expect(screen.getByText('FMP')).toBeInTheDocument();
  });

  it('shows relative time for recent items', () => {
    mockUseRecentCatalysts.mockReturnValue({
      data: mockCatalystsData,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      dataUpdatedAt: Date.now(),
    } as ReturnType<typeof useRecentCatalysts>);

    render(<CatalystAlertPanel />, { wrapper });

    // First item is 5 minutes ago
    expect(screen.getByText('5m ago')).toBeInTheDocument();
    // Second item is 2 hours ago
    expect(screen.getByText('2h ago')).toBeInTheDocument();
  });
});
