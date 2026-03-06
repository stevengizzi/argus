/**
 * Tests for TickerText component.
 *
 * Sprint 22, Fix Session.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TickerText } from '../TickerText';

describe('TickerText', () => {
  it('renders plain text without tickers unchanged', () => {
    render(<TickerText>Hello world</TickerText>);

    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });

  it('highlights single ticker symbol', () => {
    render(<TickerText>Check out $AAPL today</TickerText>);

    const ticker = screen.getByText('$AAPL');
    expect(ticker).toBeInTheDocument();
    expect(ticker).toHaveClass('text-argus-accent');
  });

  it('highlights multiple ticker symbols', () => {
    render(<TickerText>Compare $AAPL vs $GOOGL performance</TickerText>);

    const aapl = screen.getByText('$AAPL');
    const googl = screen.getByText('$GOOGL');

    expect(aapl).toHaveClass('text-argus-accent');
    expect(googl).toHaveClass('text-argus-accent');
  });

  it('handles ticker at start of text', () => {
    render(<TickerText>$NVDA is trending</TickerText>);

    const ticker = screen.getByText('$NVDA');
    expect(ticker).toHaveClass('text-argus-accent');
    expect(screen.getByText(/is trending/)).toBeInTheDocument();
  });

  it('handles ticker at end of text', () => {
    render(<TickerText>Consider buying $TSLA</TickerText>);

    const ticker = screen.getByText('$TSLA');
    expect(ticker).toHaveClass('text-argus-accent');
    expect(screen.getByText(/Consider buying/)).toBeInTheDocument();
  });

  it('passes through non-string children unchanged', () => {
    render(
      <TickerText>
        <span data-testid="nested">Nested content</span>
      </TickerText>
    );

    expect(screen.getByTestId('nested')).toBeInTheDocument();
  });

  it('does not highlight invalid ticker patterns', () => {
    render(<TickerText>$ alone or $123 numbers</TickerText>);

    // Should not have any highlighted tickers
    const allSpans = document.querySelectorAll('.text-argus-accent');
    expect(allSpans.length).toBe(0);
  });
});
