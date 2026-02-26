/**
 * Tests for SymbolDetailPanel component.
 *
 * Sprint 21a, Session 7.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SymbolDetailPanel } from './SymbolDetailPanel';
import { useSymbolDetailUI } from '../../stores/symbolDetailUI';

// Mock the child components to isolate testing
vi.mock('./SymbolChart', () => ({
  SymbolChart: ({ symbol }: { symbol: string }) => (
    <div data-testid="symbol-chart">Chart for {symbol}</div>
  ),
}));

vi.mock('./SymbolTradingHistory', () => ({
  SymbolTradingHistory: ({ symbol }: { symbol: string }) => (
    <div data-testid="symbol-trading-history">Trading history for {symbol}</div>
  ),
}));

vi.mock('./SymbolPositionDetail', () => ({
  SymbolPositionDetail: ({ symbol }: { symbol: string }) => (
    <div data-testid="symbol-position-detail">Position for {symbol}</div>
  ),
}));

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

// Wrapper component with providers
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

describe('SymbolDetailPanel', () => {
  beforeEach(() => {
    // Reset the Zustand store before each test
    useSymbolDetailUI.setState({
      selectedSymbol: null,
      isOpen: false,
    });
  });

  it('renders nothing when no symbol is selected', () => {
    render(
      <TestWrapper>
        <SymbolDetailPanel />
      </TestWrapper>
    );

    // Nothing should be rendered
    expect(screen.queryByTestId('symbol-chart')).not.toBeInTheDocument();
  });

  it('renders symbol name when opened', () => {
    // Open the panel with a symbol
    useSymbolDetailUI.getState().open('AAPL');

    render(
      <TestWrapper>
        <SymbolDetailPanel />
      </TestWrapper>
    );

    // Symbol name appears in the panel title
    expect(screen.getByText('AAPL')).toBeInTheDocument();
  });

  it('shows chart section', () => {
    useSymbolDetailUI.getState().open('TSLA');

    render(
      <TestWrapper>
        <SymbolDetailPanel />
      </TestWrapper>
    );

    // Chart placeholder is rendered
    expect(screen.getByTestId('symbol-chart')).toBeInTheDocument();
    expect(screen.getByText('Chart for TSLA')).toBeInTheDocument();
  });

  it('shows trading history section', () => {
    useSymbolDetailUI.getState().open('NVDA');

    render(
      <TestWrapper>
        <SymbolDetailPanel />
      </TestWrapper>
    );

    // Trading history is rendered
    expect(screen.getByTestId('symbol-trading-history')).toBeInTheDocument();
    expect(screen.getByText('Trading history for NVDA')).toBeInTheDocument();
  });

  it('shows position detail section', () => {
    useSymbolDetailUI.getState().open('AMD');

    render(
      <TestWrapper>
        <SymbolDetailPanel />
      </TestWrapper>
    );

    // Position detail is rendered
    expect(screen.getByTestId('symbol-position-detail')).toBeInTheDocument();
    expect(screen.getByText('Position for AMD')).toBeInTheDocument();
  });
});
