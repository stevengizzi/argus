/**
 * Individual briefing card for the Briefings list.
 *
 * Displays date, type badge, status badge, title, content preview,
 * word count, reading time, author, and action icons.
 */

import { BookOpen, Pencil, Trash2 } from 'lucide-react';
import { Card } from '../../../components/Card';
import { Badge } from '../../../components/Badge';
import type { Briefing } from '../../../api/types';

interface BriefingCardProps {
  briefing: Briefing;
  onEdit: () => void;
  onRead: () => void;
  onDelete: () => void;
}

type BadgeVariant = 'info' | 'success' | 'warning' | 'danger' | 'neutral';

/**
 * Format date to readable format (MMM DD, YYYY).
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Get badge variant for briefing type.
 */
function getTypeBadgeVariant(type: Briefing['briefing_type']): BadgeVariant {
  return type === 'pre_market' ? 'info' : 'warning';
}

/**
 * Get display label for briefing type.
 */
function getTypeLabel(type: Briefing['briefing_type']): string {
  return type === 'pre_market' ? 'Pre-Market' : 'End of Day';
}

/**
 * Get badge variant for status.
 */
function getStatusBadgeVariant(status: Briefing['status']): BadgeVariant {
  switch (status) {
    case 'final':
      return 'success';
    case 'ai_generated':
      return 'info';
    case 'draft':
    default:
      return 'neutral';
  }
}

/**
 * Get display label for status.
 */
function getStatusLabel(status: Briefing['status']): string {
  switch (status) {
    case 'final':
      return 'Final';
    case 'ai_generated':
      return 'AI Generated';
    case 'draft':
    default:
      return 'Draft';
  }
}

/**
 * Extract plain text preview from markdown content.
 */
function getContentPreview(content: string, maxLength: number = 150): string {
  // Remove markdown headers, bold, italics, etc.
  const plainText = content
    .replace(/^#{1,6}\s+/gm, '') // Remove headers
    .replace(/\*\*([^*]+)\*\*/g, '$1') // Remove bold
    .replace(/\*([^*]+)\*/g, '$1') // Remove italics
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Remove links
    .replace(/`([^`]+)`/g, '$1') // Remove inline code
    .replace(/\n+/g, ' ') // Replace newlines with spaces
    .trim();

  if (plainText.length <= maxLength) {
    return plainText;
  }

  return plainText.slice(0, maxLength).trim() + '...';
}

export function BriefingCard({ briefing, onEdit, onRead, onDelete }: BriefingCardProps) {
  const typeBadgeVariant = getTypeBadgeVariant(briefing.briefing_type);
  const typeLabel = getTypeLabel(briefing.briefing_type);
  const statusBadgeVariant = getStatusBadgeVariant(briefing.status);
  const statusLabel = getStatusLabel(briefing.status);
  const contentPreview = getContentPreview(briefing.content);

  return (
    <Card
      interactive
      onClick={onRead}
      className="hover:border-argus-text-dim transition-colors cursor-pointer"
    >
      {/* Main content area */}
      <div className="space-y-2">
        {/* Top row: date + badges */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-argus-text-dim">
            {formatDate(briefing.date)}
          </span>
          <Badge variant={typeBadgeVariant}>{typeLabel}</Badge>
          <Badge variant={statusBadgeVariant}>{statusLabel}</Badge>
        </div>

        {/* Title */}
        <h3 className="text-base font-semibold text-argus-text">
          {briefing.title}
        </h3>

        {/* Content preview */}
        {contentPreview && (
          <p className="text-sm text-argus-text-dim line-clamp-2">
            {contentPreview}
          </p>
        )}
      </div>

      {/* Bottom row: metadata + actions */}
      <div className="flex items-center justify-between pt-3 mt-3 border-t border-argus-border/50">
        <div className="flex items-center gap-4 text-xs text-argus-text-dim">
          <span>{briefing.word_count.toLocaleString()} words</span>
          <span>{briefing.reading_time_min} min read</span>
          <span className="capitalize">{briefing.author}</span>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRead();
            }}
            className="p-1.5 rounded text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2 transition-colors"
            aria-label="Read briefing"
            title="Read"
          >
            <BookOpen className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="p-1.5 rounded text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2 transition-colors"
            aria-label="Edit briefing"
            title="Edit"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1.5 rounded text-argus-text-dim hover:text-argus-loss hover:bg-argus-loss/10 transition-colors"
            aria-label="Delete briefing"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </Card>
  );
}
