/**
 * Tests for BriefingCard component.
 *
 * Sprint 21c, Session 10.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BriefingCard } from '../briefings/BriefingCard';
import type { Briefing } from '../../../api/types';

// Mock briefing data
const mockBriefing: Briefing = {
  id: 'briefing-001',
  date: '2026-02-27',
  briefing_type: 'pre_market',
  status: 'draft',
  title: 'Morning Market Outlook',
  content: 'Today we are watching **TSLA** and NVDA for breakout opportunities. The market regime is trending with moderate volatility.',
  metadata: null,
  author: 'operator',
  created_at: '2026-02-27T08:00:00Z',
  updated_at: '2026-02-27T08:30:00Z',
  word_count: 125,
  reading_time_min: 1,
};

const mockEodBriefing: Briefing = {
  ...mockBriefing,
  id: 'briefing-002',
  briefing_type: 'eod',
  status: 'final',
  title: 'End of Day Review',
};

const mockAiBriefing: Briefing = {
  ...mockBriefing,
  id: 'briefing-003',
  status: 'ai_generated',
  title: 'AI Generated Analysis',
};

describe('BriefingCard', () => {
  it('renders briefing title and content preview', () => {
    const handlers = {
      onEdit: vi.fn(),
      onRead: vi.fn(),
      onDelete: vi.fn(),
    };

    render(<BriefingCard briefing={mockBriefing} {...handlers} />);

    // Title
    expect(screen.getByText('Morning Market Outlook')).toBeInTheDocument();

    // Content preview (markdown should be stripped)
    expect(screen.getByText(/Today we are watching TSLA and NVDA/)).toBeInTheDocument();

    // Metadata
    expect(screen.getByText('125 words')).toBeInTheDocument();
    expect(screen.getByText('1 min read')).toBeInTheDocument();
    expect(screen.getByText('operator')).toBeInTheDocument();
  });

  it('shows correct type badge (pre_market vs eod)', () => {
    const handlers = {
      onEdit: vi.fn(),
      onRead: vi.fn(),
      onDelete: vi.fn(),
    };

    // Pre-market badge
    const { rerender } = render(<BriefingCard briefing={mockBriefing} {...handlers} />);
    expect(screen.getByText('Pre-Market')).toBeInTheDocument();

    // EOD badge
    rerender(<BriefingCard briefing={mockEodBriefing} {...handlers} />);
    expect(screen.getByText('End of Day')).toBeInTheDocument();
  });

  it('shows correct status badge', () => {
    const handlers = {
      onEdit: vi.fn(),
      onRead: vi.fn(),
      onDelete: vi.fn(),
    };

    // Draft status
    const { rerender } = render(<BriefingCard briefing={mockBriefing} {...handlers} />);
    expect(screen.getByText('Draft')).toBeInTheDocument();

    // Final status
    rerender(<BriefingCard briefing={mockEodBriefing} {...handlers} />);
    expect(screen.getByText('Final')).toBeInTheDocument();

    // AI Generated status
    rerender(<BriefingCard briefing={mockAiBriefing} {...handlers} />);
    expect(screen.getByText('AI Generated')).toBeInTheDocument();
  });

  it('calls onRead when card body is clicked', () => {
    const handlers = {
      onEdit: vi.fn(),
      onRead: vi.fn(),
      onDelete: vi.fn(),
    };

    render(<BriefingCard briefing={mockBriefing} {...handlers} />);

    // Click on the title (part of the clickable card body)
    const title = screen.getByText('Morning Market Outlook');
    fireEvent.click(title);

    expect(handlers.onRead).toHaveBeenCalledTimes(1);
    expect(handlers.onEdit).not.toHaveBeenCalled();
    expect(handlers.onDelete).not.toHaveBeenCalled();
  });

  it('calls onEdit when edit button is clicked', () => {
    const handlers = {
      onEdit: vi.fn(),
      onRead: vi.fn(),
      onDelete: vi.fn(),
    };

    render(<BriefingCard briefing={mockBriefing} {...handlers} />);

    // Click the edit button
    const editButton = screen.getByLabelText('Edit briefing');
    fireEvent.click(editButton);

    expect(handlers.onEdit).toHaveBeenCalledTimes(1);
  });

  it('calls onDelete when delete button is clicked', () => {
    const handlers = {
      onEdit: vi.fn(),
      onRead: vi.fn(),
      onDelete: vi.fn(),
    };

    render(<BriefingCard briefing={mockBriefing} {...handlers} />);

    // Click the delete button
    const deleteButton = screen.getByLabelText('Delete briefing');
    fireEvent.click(deleteButton);

    expect(handlers.onDelete).toHaveBeenCalledTimes(1);
  });
});
