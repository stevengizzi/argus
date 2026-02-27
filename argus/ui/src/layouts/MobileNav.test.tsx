/**
 * Tests for MobileNav component.
 *
 * Sprint 21d, Session 3 — Navigation restructure.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { MobileNav } from './MobileNav';

function renderWithRouter(ui: React.ReactElement, initialRoute = '/') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      {ui}
    </MemoryRouter>
  );
}

describe('MobileNav', () => {
  it('renders 5 tab items including More', () => {
    renderWithRouter(<MobileNav />);

    expect(screen.getByText('Dash')).toBeInTheDocument();
    expect(screen.getByText('Trades')).toBeInTheDocument();
    expect(screen.getByText('Orch')).toBeInTheDocument();
    expect(screen.getByText('Patterns')).toBeInTheDocument();
    expect(screen.getByText('More')).toBeInTheDocument();
  });

  it('opens MoreSheet when More tab is clicked', () => {
    renderWithRouter(<MobileNav />);

    // Sheet should not be visible initially
    expect(screen.queryByText('Performance')).not.toBeInTheDocument();

    // Click the More button
    fireEvent.click(screen.getByText('More'));

    // Sheet items should now be visible
    expect(screen.getByText('Performance')).toBeInTheDocument();
    expect(screen.getByText('The Debrief')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
  });

  it('shows active indicator on More tab when on Performance route', () => {
    renderWithRouter(<MobileNav />, '/performance');

    // The More button should have the accent color class when on a More route
    const moreButton = screen.getByText('More').closest('button');
    expect(moreButton).toHaveClass('text-argus-accent');
  });
});
