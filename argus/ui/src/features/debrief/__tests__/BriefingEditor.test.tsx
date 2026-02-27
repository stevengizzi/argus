/**
 * Tests for BriefingEditor component.
 *
 * Sprint 21c, Session 10.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { Briefing } from '../../../api/types';

// Mock the hooks before importing the component
const mockBriefing: Briefing = {
  id: 'briefing-001',
  date: '2026-02-27',
  briefing_type: 'pre_market',
  status: 'draft',
  title: 'Morning Market Outlook',
  content: '# Summary\n\nToday we watch TSLA.',
  metadata: null,
  author: 'operator',
  created_at: '2026-02-27T08:00:00Z',
  updated_at: '2026-02-27T08:30:00Z',
  word_count: 125,
  reading_time_min: 1,
};

const mockMutateAsync = vi.fn().mockResolvedValue(mockBriefing);

vi.mock('../../../hooks/useBriefings', () => ({
  useBriefing: () => ({
    data: mockBriefing,
    isLoading: false,
  }),
  useUpdateBriefing: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
    error: null,
  }),
}));

// Import after mocking
import { BriefingEditor } from '../briefings/BriefingEditor';

describe('BriefingEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders title input and content textarea', () => {
    const onClose = vi.fn();

    render(<BriefingEditor briefingId="briefing-001" onClose={onClose} />);

    // Title input
    const titleInput = screen.getByPlaceholderText('Briefing title...');
    expect(titleInput).toBeInTheDocument();
    expect(titleInput).toHaveValue('Morning Market Outlook');

    // Content textareas (desktop and mobile versions both exist in DOM)
    const textareas = screen.getAllByPlaceholderText('Write your briefing in markdown...');
    expect(textareas.length).toBeGreaterThanOrEqual(1);
  });

  it('shows preview toggle (Write/Preview tabs on desktop)', () => {
    const onClose = vi.fn();

    render(<BriefingEditor briefingId="briefing-001" onClose={onClose} />);

    // Desktop and mobile versions both exist, so there are multiple Write/Preview labels
    const writeLabels = screen.getAllByText('Write');
    const previewLabels = screen.getAllByText('Preview');
    expect(writeLabels.length).toBeGreaterThanOrEqual(1);
    expect(previewLabels.length).toBeGreaterThanOrEqual(1);
  });

  it('renders status selector with Draft/Final options', () => {
    const onClose = vi.fn();

    render(<BriefingEditor briefingId="briefing-001" onClose={onClose} />);

    // Status selector tabs
    expect(screen.getByText('Draft')).toBeInTheDocument();
    expect(screen.getByText('Final')).toBeInTheDocument();
  });

  it('renders save and cancel buttons', () => {
    const onClose = vi.fn();

    render(<BriefingEditor briefingId="briefing-001" onClose={onClose} />);

    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('shows Edit Briefing header', () => {
    const onClose = vi.fn();

    render(<BriefingEditor briefingId="briefing-001" onClose={onClose} />);

    expect(screen.getByText('Edit Briefing')).toBeInTheDocument();
  });
});
