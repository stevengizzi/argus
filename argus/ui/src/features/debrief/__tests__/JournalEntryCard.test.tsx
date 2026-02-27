/**
 * Tests for JournalEntryCard component.
 *
 * Sprint 21c, Session 10.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { JournalEntryCard } from '../journal/JournalEntryCard';
import type { JournalEntry } from '../../../api/types';

// Mock the Zustand store
vi.mock('../../../stores/debriefUI', () => ({
  useDebriefUI: () => ({
    journalDraftExpanded: false,
    setJournalDraftExpanded: vi.fn(),
  }),
}));

// Mock strategy hooks
vi.mock('../../../hooks/useStrategies', () => ({
  useStrategies: () => ({
    data: { strategies: [] },
  }),
}));

// Mock journal hooks
vi.mock('../../../hooks/useJournal', () => ({
  useCreateJournalEntry: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    isSuccess: false,
  }),
  useUpdateJournalEntry: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

// Mock entries for each type
const createMockEntry = (type: JournalEntry['entry_type']): JournalEntry => ({
  id: `entry-${type}`,
  entry_type: type,
  title: `Test ${type} entry`,
  content: 'This is the content of the journal entry. It contains some observations about today\'s trading session.',
  author: 'operator',
  linked_strategy_id: null,
  linked_trade_ids: [],
  tags: ['test', 'example'],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
});

const mockObservation = createMockEntry('observation');
const mockTradeAnnotation = createMockEntry('trade_annotation');
const mockPatternNote = createMockEntry('pattern_note');
const mockSystemNote = createMockEntry('system_note');

const mockEntryWithTrades: JournalEntry = {
  ...mockObservation,
  id: 'entry-with-trades',
  linked_trade_ids: ['trade-001', 'trade-002', 'trade-003'],
};

const mockEntryWithStrategy: JournalEntry = {
  ...mockObservation,
  id: 'entry-with-strategy',
  linked_strategy_id: 'orb_breakout',
};

describe('JournalEntryCard', () => {
  const defaultHandlers = {
    onEdit: vi.fn(),
    onEditCancel: vi.fn(),
    onDelete: vi.fn(),
  };

  it('renders entry type badge correctly for each type', () => {
    const { rerender } = render(
      <JournalEntryCard entry={mockObservation} {...defaultHandlers} />
    );
    expect(screen.getByText('Observation')).toBeInTheDocument();

    rerender(<JournalEntryCard entry={mockTradeAnnotation} {...defaultHandlers} />);
    expect(screen.getByText('Trade Annotation')).toBeInTheDocument();

    rerender(<JournalEntryCard entry={mockPatternNote} {...defaultHandlers} />);
    expect(screen.getByText('Pattern Note')).toBeInTheDocument();

    rerender(<JournalEntryCard entry={mockSystemNote} {...defaultHandlers} />);
    expect(screen.getByText('System Note')).toBeInTheDocument();
  });

  it('shows title and content preview', () => {
    render(<JournalEntryCard entry={mockObservation} {...defaultHandlers} />);

    // Title
    expect(screen.getByText('Test observation entry')).toBeInTheDocument();

    // Content preview (should be truncated)
    expect(screen.getByText(/This is the content of the journal entry/)).toBeInTheDocument();
  });

  it('displays tags', () => {
    render(<JournalEntryCard entry={mockObservation} {...defaultHandlers} />);

    expect(screen.getByText('test')).toBeInTheDocument();
    expect(screen.getByText('example')).toBeInTheDocument();
  });

  it('shows linked trade count badge', () => {
    render(<JournalEntryCard entry={mockEntryWithTrades} {...defaultHandlers} />);

    expect(screen.getByText('3 trades')).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', () => {
    const handlers = {
      onEdit: vi.fn(),
      onEditCancel: vi.fn(),
      onDelete: vi.fn(),
    };

    render(<JournalEntryCard entry={mockObservation} {...handlers} />);

    const editButton = screen.getByLabelText('Edit entry');
    fireEvent.click(editButton);

    expect(handlers.onEdit).toHaveBeenCalledTimes(1);
  });

  it('calls onDelete when delete button is clicked', () => {
    const handlers = {
      onEdit: vi.fn(),
      onEditCancel: vi.fn(),
      onDelete: vi.fn(),
    };

    render(<JournalEntryCard entry={mockObservation} {...handlers} />);

    const deleteButton = screen.getByLabelText('Delete entry');
    fireEvent.click(deleteButton);

    expect(handlers.onDelete).toHaveBeenCalledTimes(1);
  });
});
