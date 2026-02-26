/**
 * Tests for SlideInPanel component.
 *
 * Sprint 21a, Session 7.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SlideInPanel } from './SlideInPanel';

describe('SlideInPanel', () => {
  it('renders when isOpen is true', () => {
    const handleClose = vi.fn();

    render(
      <SlideInPanel
        isOpen={true}
        onClose={handleClose}
        title="Test Panel"
      >
        <div>Panel content</div>
      </SlideInPanel>
    );

    // Title is visible
    expect(screen.getByText('Test Panel')).toBeInTheDocument();

    // Content is visible
    expect(screen.getByText('Panel content')).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    const handleClose = vi.fn();

    render(
      <SlideInPanel
        isOpen={false}
        onClose={handleClose}
        title="Test Panel"
      >
        <div>Panel content</div>
      </SlideInPanel>
    );

    // Title should not be visible
    expect(screen.queryByText('Test Panel')).not.toBeInTheDocument();

    // Content should not be visible
    expect(screen.queryByText('Panel content')).not.toBeInTheDocument();
  });

  it('calls onClose when X button is clicked', () => {
    const handleClose = vi.fn();

    render(
      <SlideInPanel
        isOpen={true}
        onClose={handleClose}
        title="Test Panel"
      >
        <div>Panel content</div>
      </SlideInPanel>
    );

    // Click the close button
    const closeButton = screen.getByRole('button', { name: /close panel/i });
    fireEvent.click(closeButton);

    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('renders subtitle when provided', () => {
    const handleClose = vi.fn();

    render(
      <SlideInPanel
        isOpen={true}
        onClose={handleClose}
        title="Test Panel"
        subtitle="Test Subtitle"
      >
        <div>Panel content</div>
      </SlideInPanel>
    );

    // Subtitle is visible
    expect(screen.getByText('Test Subtitle')).toBeInTheDocument();
  });
});
