/**
 * Tests for Sidebar component.
 *
 * Sprint 21d, Session 3 — Navigation restructure.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Sidebar } from './Sidebar';

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe('Sidebar', () => {
  it('renders 7 navigation items', () => {
    renderWithRouter(<Sidebar />);

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Trades')).toBeInTheDocument();
    expect(screen.getByText('Performance')).toBeInTheDocument();
    expect(screen.getByText('Orchestrator')).toBeInTheDocument();
    expect(screen.getByText('Pattern Library')).toBeInTheDocument();
    expect(screen.getByText('The Debrief')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
  });

  it('renders dividers between navigation groups', () => {
    const { container } = renderWithRouter(<Sidebar />);

    // There should be 3 dividers:
    // - After Performance (end of Monitor group)
    // - After Patterns (end of Operate group)
    // - After Debrief (end of Learn group)
    const dividers = container.querySelectorAll('.w-8.border-b.border-argus-border');
    expect(dividers.length).toBe(3);
  });

  it('shows PAPER badge when paperMode is true', () => {
    renderWithRouter(<Sidebar paperMode={true} />);

    expect(screen.getByText('PAPER')).toBeInTheDocument();
  });

  it('does not show PAPER badge when paperMode is false', () => {
    renderWithRouter(<Sidebar paperMode={false} />);

    expect(screen.queryByText('PAPER')).not.toBeInTheDocument();
  });
});
