/**
 * Tests for ResearchDocCard component.
 *
 * Sprint 21c, Session 10.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResearchDocCard } from '../research/ResearchDocCard';
import type { ResearchDocument } from '../../../api/types';

// Mock filesystem document (read-only)
const mockFilesystemDoc: ResearchDocument = {
  id: 'doc-001',
  category: 'research',
  title: 'Market Data Infrastructure Research',
  content: '# Overview\n\nThis document covers market data options.',
  author: 'system',
  tags: ['infrastructure', 'data', 'market'],
  word_count: 2500,
  reading_time_min: 10,
  source: 'filesystem',
  is_editable: false,
  created_at: null,
  updated_at: null,
  last_modified: new Date().toISOString(),
};

// Mock database document (editable)
const mockDatabaseDoc: ResearchDocument = {
  id: 'doc-002',
  category: 'strategy',
  title: 'ORB Breakout Analysis',
  content: '# ORB Strategy\n\nDetails about the ORB strategy.',
  author: 'operator',
  tags: ['orb', 'breakout'],
  word_count: 1200,
  reading_time_min: 5,
  source: 'database',
  is_editable: true,
  created_at: new Date(Date.now() - 2 * 86400_000).toISOString(),
  updated_at: new Date(Date.now() - 86400_000).toISOString(),
  last_modified: null,
};

// Mock AI report document
const mockAiReportDoc: ResearchDocument = {
  ...mockDatabaseDoc,
  id: 'doc-003',
  category: 'ai_report',
  title: 'AI Performance Analysis',
  tags: ['ai', 'analysis'],
};

describe('ResearchDocCard', () => {
  it('renders document title and category badge', () => {
    const onRead = vi.fn();

    render(<ResearchDocCard document={mockFilesystemDoc} onRead={onRead} />);

    // Title
    expect(screen.getByText('Market Data Infrastructure Research')).toBeInTheDocument();

    // Category badge
    expect(screen.getByText('Research')).toBeInTheDocument();

    // Metadata
    expect(screen.getByText('2,500 words')).toBeInTheDocument();
    expect(screen.getByText('10 min read')).toBeInTheDocument();
  });

  it('shows tags', () => {
    const onRead = vi.fn();

    render(<ResearchDocCard document={mockFilesystemDoc} onRead={onRead} />);

    expect(screen.getByText('infrastructure')).toBeInTheDocument();
    expect(screen.getByText('data')).toBeInTheDocument();
    expect(screen.getByText('market')).toBeInTheDocument();
  });

  it('shows edit/delete only for editable docs', () => {
    const handlers = {
      onRead: vi.fn(),
      onEdit: vi.fn(),
      onDelete: vi.fn(),
    };

    // Editable doc should show edit and delete buttons
    const { rerender } = render(<ResearchDocCard document={mockDatabaseDoc} {...handlers} />);

    expect(screen.getByLabelText('Edit document')).toBeInTheDocument();
    expect(screen.getByLabelText('Delete document')).toBeInTheDocument();

    // Non-editable doc should NOT show edit and delete buttons
    rerender(<ResearchDocCard document={mockFilesystemDoc} {...handlers} />);

    expect(screen.queryByLabelText('Edit document')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Delete document')).not.toBeInTheDocument();
  });

  it('shows correct source badge (Repo vs Custom)', () => {
    const onRead = vi.fn();

    // Filesystem doc shows "Repo" badge
    const { rerender } = render(<ResearchDocCard document={mockFilesystemDoc} onRead={onRead} />);
    expect(screen.getByText('Repo')).toBeInTheDocument();

    // Database doc shows "Custom" badge
    rerender(<ResearchDocCard document={mockDatabaseDoc} onRead={onRead} />);
    expect(screen.getByText('Custom')).toBeInTheDocument();
  });

  it('calls onRead when card is clicked', () => {
    const onRead = vi.fn();

    render(<ResearchDocCard document={mockFilesystemDoc} onRead={onRead} />);

    // Click on title (part of clickable area)
    fireEvent.click(screen.getByText('Market Data Infrastructure Research'));

    expect(onRead).toHaveBeenCalledTimes(1);
  });

  it('shows correct category badge colors for each category', () => {
    const onRead = vi.fn();

    // Strategy category
    const { rerender } = render(<ResearchDocCard document={mockDatabaseDoc} onRead={onRead} />);
    expect(screen.getByText('Strategy')).toBeInTheDocument();

    // AI Report category
    rerender(<ResearchDocCard document={mockAiReportDoc} onRead={onRead} />);
    expect(screen.getByText('AI Report')).toBeInTheDocument();
  });
});
