/**
 * Tests for JournalTagInput component.
 *
 * Sprint 21c, Session 10.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock the journal hooks
vi.mock('../../../hooks/useJournal', () => ({
  useJournalTags: () => ({
    data: { tags: ['trading', 'setup', 'review', 'breakout', 'analysis'] },
  }),
}));

// Import after mocking
import { JournalTagInput } from '../journal/JournalTagInput';

describe('JournalTagInput', () => {
  it('renders with existing tags as chips', () => {
    const tags = ['tag1', 'tag2', 'tag3'];
    const onChange = vi.fn();

    render(<JournalTagInput tags={tags} onChange={onChange} />);

    expect(screen.getByText('tag1')).toBeInTheDocument();
    expect(screen.getByText('tag2')).toBeInTheDocument();
    expect(screen.getByText('tag3')).toBeInTheDocument();
  });

  it('removes tag when X is clicked', () => {
    const tags = ['tag1', 'tag2'];
    const onChange = vi.fn();

    render(<JournalTagInput tags={tags} onChange={onChange} />);

    // Click the remove button for tag1
    const removeButtons = screen.getAllByRole('button', { name: /Remove/i });
    fireEvent.click(removeButtons[0]);

    // onChange should be called with tag1 removed
    expect(onChange).toHaveBeenCalledWith(['tag2']);
  });

  it('shows input field', () => {
    const onChange = vi.fn();

    render(<JournalTagInput tags={[]} onChange={onChange} />);

    expect(screen.getByPlaceholderText('Add tags...')).toBeInTheDocument();
  });

  it('adds new tag on Enter', () => {
    const onChange = vi.fn();

    render(<JournalTagInput tags={['existing']} onChange={onChange} />);

    const input = screen.getByPlaceholderText('Add tags...');
    fireEvent.change(input, { target: { value: 'newtag' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    // onChange should be called with new tag added
    expect(onChange).toHaveBeenCalledWith(['existing', 'newtag']);
  });
});
