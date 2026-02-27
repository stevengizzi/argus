/**
 * Individual journal entry card.
 *
 * Displays entry type badge, title/content preview, tags,
 * linked trades/strategy badges, timestamp, and action icons.
 */

import { Eye, Target, Lightbulb, Settings, Pencil, Trash2, Link } from 'lucide-react';
import { Card } from '../../../components/Card';
import { StrategyBadge } from '../../../components/Badge';
import type { JournalEntry, JournalEntryType } from '../../../api/types';

interface JournalEntryCardProps {
  entry: JournalEntry;
  onEdit: () => void;
  onDelete: () => void;
}

interface TypeConfig {
  icon: typeof Eye;
  colorClass: string;
  bgClass: string;
  label: string;
}

const TYPE_CONFIGS: Record<JournalEntryType, TypeConfig> = {
  observation: {
    icon: Eye,
    colorClass: 'text-blue-400',
    bgClass: 'bg-blue-400/15',
    label: 'Observation',
  },
  trade_annotation: {
    icon: Target,
    colorClass: 'text-argus-profit',
    bgClass: 'bg-argus-profit/15',
    label: 'Trade Annotation',
  },
  pattern_note: {
    icon: Lightbulb,
    colorClass: 'text-amber-400',
    bgClass: 'bg-amber-400/15',
    label: 'Pattern Note',
  },
  system_note: {
    icon: Settings,
    colorClass: 'text-argus-text-dim',
    bgClass: 'bg-argus-surface-2',
    label: 'System Note',
  },
};

/**
 * Format a date string to relative time (e.g., "2 hours ago", "3 days ago").
 */
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  const diffWeek = Math.floor(diffDay / 7);
  const diffMonth = Math.floor(diffDay / 30);

  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
  if (diffHour < 24) return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ago`;
  if (diffDay < 7) return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`;
  if (diffWeek < 4) return `${diffWeek} week${diffWeek !== 1 ? 's' : ''} ago`;
  if (diffMonth < 12) return `${diffMonth} month${diffMonth !== 1 ? 's' : ''} ago`;

  // Fallback to formatted date for older entries
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Extract plain text preview from content.
 */
function getContentPreview(content: string, maxLength: number = 120): string {
  // Remove markdown formatting
  const plainText = content
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\n+/g, ' ')
    .trim();

  if (plainText.length <= maxLength) {
    return plainText;
  }

  return plainText.slice(0, maxLength).trim() + '...';
}

export function JournalEntryCard({ entry, onEdit, onDelete }: JournalEntryCardProps) {
  const typeConfig = TYPE_CONFIGS[entry.entry_type];
  const Icon = typeConfig.icon;

  // Use title or first 60 chars of content
  const displayTitle = entry.title || getContentPreview(entry.content, 60);
  const contentPreview = entry.title ? getContentPreview(entry.content) : null;

  const hasLinkedTrades = entry.linked_trade_ids.length > 0;
  const linkedTradeCount = entry.linked_trade_ids.length;

  return (
    <Card interactive className="hover:border-argus-text-dim transition-colors">
      <div className="space-y-2">
        {/* Top row: type badge + timestamp */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Type badge */}
            <span
              className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${typeConfig.bgClass} ${typeConfig.colorClass}`}
            >
              <Icon className="w-3 h-3" />
              {typeConfig.label}
            </span>

            {/* Strategy badge */}
            {entry.linked_strategy_id && (
              <StrategyBadge strategyId={entry.linked_strategy_id} />
            )}

            {/* Linked trades badge */}
            {hasLinkedTrades && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-argus-surface-2 text-argus-text-dim">
                <Link className="w-3 h-3" />
                {linkedTradeCount} linked trade{linkedTradeCount !== 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Timestamp */}
          <span className="text-xs text-argus-text-dim">
            {formatRelativeTime(entry.created_at)}
          </span>
        </div>

        {/* Title */}
        <h3 className="text-base font-semibold text-argus-text">
          {displayTitle}
        </h3>

        {/* Content preview (only if we have a separate title) */}
        {contentPreview && (
          <p className="text-sm text-argus-text-dim line-clamp-2">
            {contentPreview}
          </p>
        )}

        {/* Tags */}
        {entry.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {entry.tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center px-2 py-0.5 text-xs rounded-full bg-argus-surface-2 text-argus-text-dim"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Bottom row: actions */}
      <div className="flex items-center justify-end gap-1 pt-3 mt-3 border-t border-argus-border/50">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          className="p-1.5 rounded text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2 transition-colors"
          aria-label="Edit entry"
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
          aria-label="Delete entry"
          title="Delete"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </Card>
  );
}
