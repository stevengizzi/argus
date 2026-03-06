/**
 * TickerText component for styling stock ticker symbols in chat messages.
 *
 * Detects $TICKER patterns (e.g., $AAPL, $TSLA) and renders them with
 * distinct styling for visual emphasis.
 *
 * Sprint 22 — AI chat enhancement.
 */

import type { ReactNode } from 'react';

// Pattern: $ followed by 1-5 uppercase letters at a word boundary
const TICKER_PATTERN = /(\$[A-Z]{1,5})\b/g;

/**
 * Check if a string contains any ticker patterns.
 */
export function containsTickers(text: string): boolean {
  return TICKER_PATTERN.test(text);
}

/**
 * Component that renders text with $TICKER patterns styled.
 *
 * Tickers are highlighted with a distinct color and font weight.
 */
export function TickerText({ children }: { children: ReactNode }): JSX.Element {
  // Only process string children
  if (typeof children !== 'string') {
    return <>{children}</>;
  }

  // Reset regex lastIndex since it's global
  TICKER_PATTERN.lastIndex = 0;

  // Check if there are any tickers
  if (!TICKER_PATTERN.test(children)) {
    return <>{children}</>;
  }

  // Reset again for split
  TICKER_PATTERN.lastIndex = 0;

  // Split the text by ticker pattern, keeping the delimiters
  const parts = children.split(TICKER_PATTERN);

  if (parts.length === 1) {
    return <>{children}</>;
  }

  return (
    <>
      {parts.map((part, index) => {
        // Reset lastIndex before each test
        TICKER_PATTERN.lastIndex = 0;
        if (TICKER_PATTERN.test(part)) {
          return (
            <span
              key={index}
              className="font-semibold text-argus-accent"
            >
              {part}
            </span>
          );
        }
        return <span key={index}>{part}</span>;
      })}
    </>
  );
}
