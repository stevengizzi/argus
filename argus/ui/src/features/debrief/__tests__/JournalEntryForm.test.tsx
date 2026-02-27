/**
 * Tests for JournalEntryForm component.
 *
 * Sprint 21c, Session 10.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Track Zustand store state
let mockDraftExpanded = false;
const mockSetJournalDraftExpanded = vi.fn((value: boolean) => {
  mockDraftExpanded = value;
});

// Mock the Zustand store
vi.mock('../../../stores/debriefUI', () => ({
  useDebriefUI: (selector: (state: { journalDraftExpanded: boolean; setJournalDraftExpanded: (v: boolean) => void }) => unknown) => {
    const state = {
      journalDraftExpanded: mockDraftExpanded,
      setJournalDraftExpanded: mockSetJournalDraftExpanded,
    };
    return selector(state);
  },
}));

// Mock strategy hooks
vi.mock('../../../hooks/useStrategies', () => ({
  useStrategies: () => ({
    data: {
      strategies: [
        { strategy_id: 'orb_breakout', name: 'ORB Breakout' },
        { strategy_id: 'vwap_reclaim', name: 'VWAP Reclaim' },
      ],
    },
  }),
}));

// Mock journal hooks
const mockCreateMutateAsync = vi.fn().mockResolvedValue({});
const mockUpdateMutateAsync = vi.fn().mockResolvedValue({});

vi.mock('../../../hooks/useJournal', () => ({
  useCreateJournalEntry: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
    isSuccess: false,
  }),
  useUpdateJournalEntry: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
  useJournalTags: () => ({
    data: { tags: ['trading', 'setup', 'review'] },
  }),
}));

// Import after mocking
import { JournalEntryForm } from '../journal/JournalEntryForm';

describe('JournalEntryForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDraftExpanded = false;
  });

  it('starts collapsed with placeholder input', () => {
    render(<JournalEntryForm />);

    // Should show the collapsed placeholder
    expect(screen.getByPlaceholderText('What did you observe today?')).toBeInTheDocument();

    // Expanded fields should NOT be visible
    expect(screen.queryByPlaceholderText('Title (brief summary)')).not.toBeInTheDocument();
  });

  it('expands on click/focus', () => {
    const { rerender } = render(<JournalEntryForm />);

    const input = screen.getByPlaceholderText('What did you observe today?');
    fireEvent.click(input);

    // Check that setJournalDraftExpanded was called with true
    expect(mockSetJournalDraftExpanded).toHaveBeenCalledWith(true);

    // Re-render with expanded state
    mockDraftExpanded = true;
    rerender(<JournalEntryForm />);

    // Expanded fields should now be visible
    expect(screen.getByPlaceholderText('Title (brief summary)')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Write your observation...')).toBeInTheDocument();
  });

  it('shows type selector when expanded', () => {
    mockDraftExpanded = true;

    render(<JournalEntryForm />);

    // Type label
    expect(screen.getByText('Type')).toBeInTheDocument();

    // Type options
    expect(screen.getByRole('button', { name: /Observation/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Trade Annotation/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Pattern Note/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /System Note/i })).toBeInTheDocument();
  });

  it('renders tag input when expanded', () => {
    mockDraftExpanded = true;

    render(<JournalEntryForm />);

    // Tags label
    expect(screen.getByText('Tags')).toBeInTheDocument();

    // Tag input placeholder
    expect(screen.getByPlaceholderText('Add tags...')).toBeInTheDocument();
  });

  it('collapses on cancel', () => {
    mockDraftExpanded = true;

    render(<JournalEntryForm />);

    // Find and click cancel button
    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    // Check that setJournalDraftExpanded was called with false
    expect(mockSetJournalDraftExpanded).toHaveBeenCalledWith(false);
  });

  it('shows strategy selector when expanded', () => {
    mockDraftExpanded = true;

    render(<JournalEntryForm />);

    // Strategy label
    expect(screen.getByText('Linked Strategy (optional)')).toBeInTheDocument();

    // Strategy dropdown should have options
    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
  });

  it('shows save button when expanded', () => {
    mockDraftExpanded = true;

    render(<JournalEntryForm />);

    expect(screen.getByRole('button', { name: /Save/i })).toBeInTheDocument();
  });
});
