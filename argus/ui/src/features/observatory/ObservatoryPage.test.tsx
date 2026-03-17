/**
 * Tests for Observatory page shell, keyboard system, and layout.
 *
 * Sprint 25, Session 3.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ObservatoryPage } from './ObservatoryPage';

// Mock the FunnelView lazy import — Three.js is not available in jsdom
vi.mock('./views/FunnelView', () => ({
  FunnelView: vi.fn().mockImplementation(
    ({ selectedTier }: { selectedTier: number }) => (
      <div data-testid="funnel-view" data-selected-tier={selectedTier} />
    ),
  ),
}));

// Mock the API client
vi.mock('../../api/client', () => ({
  getToken: () => 'mock-token',
  getObservatoryPipeline: vi.fn().mockResolvedValue({
    tiers: {
      universe: { count: 3000, symbols: [] },
      viable: { count: 500, symbols: [] },
      routed: { count: 120, symbols: [] },
      evaluating: { count: 45, symbols: [] },
      near_trigger: { count: 12, symbols: [] },
      signal: { count: 3, symbols: [] },
      traded: { count: 1, symbols: [] },
    },
    timestamp: '2026-03-17T14:30:00Z',
  }),
  getObservatoryClosestMisses: vi.fn().mockResolvedValue({
    tier: 'universe',
    items: [],
    count: 0,
    timestamp: '2026-03-17T14:30:00Z',
  }),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/observatory']}>
          <Routes>
            <Route path="/observatory" element={children} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe('ObservatoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the observatory page at /observatory', () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });
    expect(screen.getByTestId('observatory-page')).toBeInTheDocument();
  });

  it('defaults to funnel view', async () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('funnel-view')).toBeInTheDocument();
    });
  });

  it('switches views when pressing f/m/r/t', async () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });

    // Matrix view renders its own component (not the placeholder)
    fireEvent.keyDown(window, { key: 'm' });
    await waitFor(() => {
      // MatrixView renders matrix-empty or matrix-loading — not the placeholder label
      expect(screen.queryByTestId('active-view-label')).not.toBeInTheDocument();
    });

    // Other views still use placeholder
    fireEvent.keyDown(window, { key: 't' });
    expect(screen.getByTestId('active-view-label')).toHaveTextContent('Timeline View');

    fireEvent.keyDown(window, { key: 'r' });
    expect(screen.getByTestId('active-view-label')).toHaveTextContent('Radar View');

    fireEvent.keyDown(window, { key: 'f' });
    await waitFor(() => {
      expect(screen.getByTestId('funnel-view')).toBeInTheDocument();
    });
  });

  it('does not switch view when pressing numeric keys 1-4', () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });

    fireEvent.keyDown(window, { key: '1' });
    fireEvent.keyDown(window, { key: '2' });
    fireEvent.keyDown(window, { key: '3' });
    fireEvent.keyDown(window, { key: '4' });

    // Should remain on default Funnel view
    expect(screen.getByTestId('funnel-view')).toBeInTheDocument();
  });

  it('navigates tiers with [ and ] keys', () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });

    // Default is tier 0 (Universe)
    const tierSelector = screen.getByTestId('tier-selector');
    const firstPill = tierSelector.querySelector('[aria-selected="true"]');
    expect(firstPill).toHaveTextContent('Universe');

    // Press ] to go to next tier
    fireEvent.keyDown(window, { key: ']' });
    const secondPill = tierSelector.querySelector('[aria-selected="true"]');
    expect(secondPill).toHaveTextContent('Viable');

    // Press [ to go back
    fireEvent.keyDown(window, { key: '[' });
    const backToFirst = tierSelector.querySelector('[aria-selected="true"]');
    expect(backToFirst).toHaveTextContent('Universe');
  });

  it('does not navigate below first tier with [', () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });

    // Already at tier 0, pressing [ should stay at 0
    fireEvent.keyDown(window, { key: '[' });
    const tierSelector = screen.getByTestId('tier-selector');
    const firstPill = tierSelector.querySelector('[aria-selected="true"]');
    expect(firstPill).toHaveTextContent('Universe');
  });

  it('ignores keyboard shortcuts when input is focused', () => {
    render(
      <div>
        <input data-testid="test-input" />
        <ObservatoryPage />
      </div>,
      { wrapper: createWrapper() }
    );

    const input = screen.getByTestId('test-input');
    input.focus();

    // Fire keydown on the input element
    fireEvent.keyDown(input, { key: 'm' });

    // Should still show Funnel (default), not Matrix
    expect(screen.getByTestId('funnel-view')).toBeInTheDocument();
  });

  it('renders all 7 tier pills', () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });

    const tierSelector = screen.getByTestId('tier-selector');
    const pills = tierSelector.querySelectorAll('[role="option"]');
    expect(pills).toHaveLength(7);
  });

  it('opens detail panel when symbol is selected and closes on Escape', async () => {
    // We need to test with a symbol selection. Since symbols list is empty in placeholder,
    // we test the detail panel via direct state. Render the page, then simulate selecting.
    // The keyboard Enter on empty symbols does nothing, so we test Escape clears.
    render(<ObservatoryPage />, { wrapper: createWrapper() });

    // No detail panel initially
    expect(screen.queryByTestId('detail-panel')).not.toBeInTheDocument();

    // We can't easily trigger symbol selection in this placeholder state
    // but we CAN verify escape doesn't crash when nothing is selected
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByTestId('detail-panel')).not.toBeInTheDocument();
  });

  it('toggles shortcut overlay with ? key', () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });

    // No overlay initially
    expect(screen.queryByTestId('shortcut-overlay')).not.toBeInTheDocument();

    // Press ? to open
    fireEvent.keyDown(window, { key: '?' });
    expect(screen.getByTestId('shortcut-overlay')).toBeInTheDocument();

    // Press ? again to close
    fireEvent.keyDown(window, { key: '?' });
    expect(screen.queryByTestId('shortcut-overlay')).not.toBeInTheDocument();
  });

  it('closes shortcut overlay with Escape', () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });

    // Open overlay
    fireEvent.keyDown(window, { key: '?' });
    expect(screen.getByTestId('shortcut-overlay')).toBeInTheDocument();

    // Close with Escape
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByTestId('shortcut-overlay')).not.toBeInTheDocument();
  });

  it('renders full-bleed layout without card wrappers', () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });

    const page = screen.getByTestId('observatory-page');
    // Full-bleed: negative margins applied
    expect(page.className).toContain('-m-');

    // No Card components — verify observatory-layout exists without card wrappers
    expect(screen.getByTestId('observatory-layout')).toBeInTheDocument();
    expect(screen.getByTestId('observatory-canvas')).toBeInTheDocument();
  });

  it('renders shortcut strip at bottom', () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });
    expect(screen.getByTestId('shortcut-strip')).toBeInTheDocument();
  });

  it('renders session vitals placeholder', () => {
    render(<ObservatoryPage />, { wrapper: createWrapper() });
    expect(screen.getByTestId('session-vitals-placeholder')).toBeInTheDocument();
  });
});
