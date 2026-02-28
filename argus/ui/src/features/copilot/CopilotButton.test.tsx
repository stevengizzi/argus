/**
 * Tests for CopilotButton component.
 *
 * Sprint 21d, Session 11.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CopilotButton } from './CopilotButton';
import { useCopilotUIStore } from '../../stores/copilotUI';

describe('CopilotButton', () => {
  beforeEach(() => {
    // Reset the Zustand store before each test
    useCopilotUIStore.setState({
      isOpen: false,
    });
  });

  it('renders floating action button when panel is closed', () => {
    render(<CopilotButton />);

    const button = screen.getByRole('button', { name: /open ai copilot/i });
    expect(button).toBeInTheDocument();
  });

  it('hides button when panel is open', () => {
    useCopilotUIStore.setState({ isOpen: true });

    render(<CopilotButton />);

    expect(screen.queryByRole('button', { name: /open ai copilot/i })).not.toBeInTheDocument();
  });

  it('opens panel when button is clicked', () => {
    const openSpy = vi.spyOn(useCopilotUIStore.getState(), 'open');

    render(<CopilotButton />);

    const button = screen.getByRole('button', { name: /open ai copilot/i });
    fireEvent.click(button);

    expect(openSpy).toHaveBeenCalled();
  });
});
