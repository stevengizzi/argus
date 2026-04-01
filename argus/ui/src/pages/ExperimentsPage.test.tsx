/**
 * Tests for ExperimentsPage — Sprint 32.5 Session 7 (DEF-131).
 *
 * Covers: renders without error, empty state, disabled state (503), navigation entry.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApiError } from '../api/client';

// Mock hooks
vi.mock('../hooks/useExperiments', () => ({
  useExperimentVariants: vi.fn(),
  usePromotionEvents: vi.fn(),
}));

vi.mock('../hooks/useCopilotContext', () => ({
  useCopilotContext: vi.fn(),
}));

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client');
  return { ...actual, getToken: vi.fn(() => null) };
});

import { useExperimentVariants, usePromotionEvents } from '../hooks/useExperiments';

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe('ExperimentsPage — renders without error', () => {
  beforeEach(() => {
    vi.mocked(useExperimentVariants).mockReturnValue({
      data: { variants: [], count: 0, timestamp: new Date().toISOString() },
      error: null,
      isLoading: false,
    } as ReturnType<typeof useExperimentVariants>);
    vi.mocked(usePromotionEvents).mockReturnValue({
      data: { events: [], total_count: 0, limit: 50, offset: 0, timestamp: new Date().toISOString() },
      error: null,
      isLoading: false,
    } as ReturnType<typeof usePromotionEvents>);
  });

  it('mounts and shows page heading', async () => {
    const { ExperimentsPage } = await import('./ExperimentsPage');
    render(<ExperimentsPage />, { wrapper: makeWrapper() });
    expect(screen.getByText('Experiments')).toBeInTheDocument();
  });
});

describe('ExperimentsPage — empty state', () => {
  beforeEach(() => {
    vi.mocked(useExperimentVariants).mockReturnValue({
      data: { variants: [], count: 0, timestamp: new Date().toISOString() },
      error: null,
      isLoading: false,
    } as ReturnType<typeof useExperimentVariants>);
    vi.mocked(usePromotionEvents).mockReturnValue({
      data: { events: [], total_count: 0, limit: 50, offset: 0, timestamp: new Date().toISOString() },
      error: null,
      isLoading: false,
    } as ReturnType<typeof usePromotionEvents>);
  });

  it('shows empty state message when no variants exist', async () => {
    const { ExperimentsPage } = await import('./ExperimentsPage');
    render(<ExperimentsPage />, { wrapper: makeWrapper() });
    expect(screen.getByTestId('experiments-empty')).toBeInTheDocument();
    expect(screen.getByText(/No experiments have been run yet/i)).toBeInTheDocument();
  });

  it('shows empty promotions message when no events', async () => {
    const { ExperimentsPage } = await import('./ExperimentsPage');
    render(<ExperimentsPage />, { wrapper: makeWrapper() });
    expect(screen.getByTestId('promotions-empty')).toBeInTheDocument();
  });
});

describe('ExperimentsPage — disabled state', () => {
  beforeEach(() => {
    const err = new ApiError('Experiment pipeline not available', 503);
    vi.mocked(useExperimentVariants).mockReturnValue({
      data: undefined,
      error: err,
      isLoading: false,
    } as ReturnType<typeof useExperimentVariants>);
    vi.mocked(usePromotionEvents).mockReturnValue({
      data: undefined,
      error: null,
      isLoading: false,
    } as ReturnType<typeof usePromotionEvents>);
  });

  it('shows disabled message when experiments.enabled=false (503)', async () => {
    const { ExperimentsPage } = await import('./ExperimentsPage');
    render(<ExperimentsPage />, { wrapper: makeWrapper() });
    expect(screen.getByTestId('experiments-disabled')).toBeInTheDocument();
    expect(screen.getByText(/Experiment pipeline is not enabled/i)).toBeInTheDocument();
    expect(screen.getByText(/config\/experiments\.yaml/i)).toBeInTheDocument();
  });
});

describe('ExperimentsPage — variant table', () => {
  beforeEach(() => {
    vi.mocked(useExperimentVariants).mockReturnValue({
      data: {
        variants: [
          {
            variant_id: 'var-aaa-111',
            pattern_name: 'bull_flag',
            detection_params: {},
            exit_overrides: null,
            config_fingerprint: 'abc123def456',
            mode: 'shadow',
            status: 'pending',
            trade_count: 0,
            shadow_trade_count: 12,
            win_rate: 0.58,
            expectancy: 0.45,
            sharpe: 1.2,
          },
          {
            variant_id: 'var-bbb-222',
            pattern_name: 'bull_flag',
            detection_params: {},
            exit_overrides: null,
            config_fingerprint: 'xyz789uvw012',
            mode: 'live',
            status: 'active',
            trade_count: 5,
            shadow_trade_count: 0,
            win_rate: 0.60,
            expectancy: 0.55,
            sharpe: 1.5,
          },
        ],
        count: 2,
        timestamp: new Date().toISOString(),
      },
      error: null,
      isLoading: false,
    } as ReturnType<typeof useExperimentVariants>);
    vi.mocked(usePromotionEvents).mockReturnValue({
      data: { events: [], total_count: 0, limit: 50, offset: 0, timestamp: new Date().toISOString() },
      error: null,
      isLoading: false,
    } as ReturnType<typeof usePromotionEvents>);
  });

  it('renders variant table with data grouped by pattern', async () => {
    const { ExperimentsPage } = await import('./ExperimentsPage');
    render(<ExperimentsPage />, { wrapper: makeWrapper() });
    expect(screen.getByTestId('variant-table')).toBeInTheDocument();
    expect(screen.getByText('bull_flag')).toBeInTheDocument();
    // Both variants listed (pattern group expanded by default)
    expect(screen.getByText('SHADOW')).toBeInTheDocument();
    expect(screen.getByText('LIVE')).toBeInTheDocument();
  });
});
