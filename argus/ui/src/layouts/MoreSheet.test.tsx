/**
 * Tests for MoreSheet component.
 *
 * Sprint 21d, Session 3 — Navigation restructure.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { MoreSheet } from './MoreSheet';

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe('MoreSheet', () => {
  it('renders 3 navigation items when open', () => {
    const handleClose = vi.fn();

    renderWithRouter(<MoreSheet isOpen={true} onClose={handleClose} />);

    expect(screen.getByText('Performance')).toBeInTheDocument();
    expect(screen.getByText('The Debrief')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
  });

  it('does not render content when closed', () => {
    const handleClose = vi.fn();

    renderWithRouter(<MoreSheet isOpen={false} onClose={handleClose} />);

    expect(screen.queryByText('Performance')).not.toBeInTheDocument();
    expect(screen.queryByText('The Debrief')).not.toBeInTheDocument();
    expect(screen.queryByText('System')).not.toBeInTheDocument();
  });

  it('calls onClose when nav item is clicked', () => {
    const handleClose = vi.fn();

    renderWithRouter(<MoreSheet isOpen={true} onClose={handleClose} />);

    fireEvent.click(screen.getByText('Performance'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
