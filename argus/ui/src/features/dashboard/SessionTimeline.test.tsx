/**
 * Tests for SessionTimeline component.
 *
 * Sprint 21d Code Review — New component for dashboard 3-card row.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SessionTimeline } from './SessionTimeline';

describe('SessionTimeline', () => {
  it('renders Session Timeline header', () => {
    render(<SessionTimeline />);

    expect(screen.getByText('Session Timeline')).toBeInTheDocument();
  });

  it('renders SVG timeline', () => {
    const { container } = render(<SessionTimeline />);

    // Check SVG is rendered
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders time labels (9:30, 12PM, 4PM)', () => {
    render(<SessionTimeline />);

    expect(screen.getByText('9:30')).toBeInTheDocument();
    expect(screen.getByText('12PM')).toBeInTheDocument();
    expect(screen.getByText('4PM')).toBeInTheDocument();
  });

  it('renders strategy bars with letters', () => {
    render(<SessionTimeline />);

    // Strategy letters should be visible
    expect(screen.getByText('O')).toBeInTheDocument(); // ORB
    expect(screen.getByText('S')).toBeInTheDocument(); // Scalp
    expect(screen.getByText('V')).toBeInTheDocument(); // VWAP
    expect(screen.getByText('A')).toBeInTheDocument(); // Afternoon
  });

  it('renders strategy window rects in SVG', () => {
    const { container } = render(<SessionTimeline />);

    // Should have multiple rect elements for strategy bars
    const rects = container.querySelectorAll('svg rect');
    // At least 5: 1 background + 4 strategy bars
    expect(rects.length).toBeGreaterThanOrEqual(5);
  });

  it('renders status text based on time', () => {
    render(<SessionTimeline />);

    // Should have some status text (varies based on current time)
    // Could be: "Pre-market...", "Active: O, S, V", "No strategies active", "After hours..."
    const statusOptions = [
      /pre-market/i,
      /active/i,
      /no strategies active/i,
      /after hours/i,
    ];

    // At least one of these should be present
    const foundStatus = statusOptions.some((pattern) => {
      try {
        screen.getByText(pattern);
        return true;
      } catch {
        return false;
      }
    });

    expect(foundStatus).toBe(true);
  });
});
