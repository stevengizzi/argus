/**
 * Individual research document card for the Research Library.
 *
 * Displays category badge, source badge, title, tags, word count,
 * reading time, and action icons for editable documents.
 */

import { BookOpen, Pencil, Trash2 } from 'lucide-react';
import { Card } from '../../../components/Card';
import type { ResearchDocument } from '../../../api/types';

interface ResearchDocCardProps {
  document: ResearchDocument;
  onRead: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

/**
 * Get category badge color classes for custom colors.
 */
function getCategoryColorClass(category: ResearchDocument['category']): string {
  switch (category) {
    case 'research':
      return 'text-blue-400 bg-blue-400/15';
    case 'strategy':
      return 'text-argus-profit bg-argus-profit-dim';
    case 'backtest':
      return 'text-amber-400 bg-amber-400/15';
    case 'ai_report':
      return 'text-purple-400 bg-purple-400/15';
    default:
      return 'text-argus-text-dim bg-argus-surface-2';
  }
}

/**
 * Get display label for category.
 */
function getCategoryLabel(category: ResearchDocument['category']): string {
  switch (category) {
    case 'research':
      return 'Research';
    case 'strategy':
      return 'Strategy';
    case 'backtest':
      return 'Backtest';
    case 'ai_report':
      return 'AI Report';
    default:
      return category;
  }
}

export function ResearchDocCard({
  document: doc,
  onRead,
  onEdit,
  onDelete,
}: ResearchDocCardProps) {
  const categoryColorClass = getCategoryColorClass(doc.category);
  const categoryLabel = getCategoryLabel(doc.category);

  return (
    <Card interactive className="hover:border-argus-text-dim transition-colors h-full flex flex-col">
      {/* Main clickable area for reading */}
      <div onClick={onRead} className="cursor-pointer flex-1 flex flex-col">
        {/* Top row: category badge + source badge */}
        <div className="flex items-center justify-between mb-2">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${categoryColorClass}`}
          >
            {categoryLabel}
          </span>

          {/* Source badge - Repo (filesystem) or Custom (database) */}
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${
              doc.source === 'filesystem'
                ? 'text-argus-text-dim border-argus-border bg-transparent'
                : 'text-argus-accent border-argus-accent/30 bg-argus-accent/10'
            }`}
          >
            {doc.source === 'filesystem' ? 'Repo' : 'Custom'}
          </span>
        </div>

        {/* Title */}
        <h3 className="text-base font-semibold text-argus-text mb-2">{doc.title}</h3>

        {/* Tags - always render container for consistent height */}
        <div className="flex flex-wrap gap-1.5 min-h-[24px] flex-1">
          {doc.tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs rounded-full bg-argus-surface-2 text-argus-text-dim h-fit"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Bottom row: metadata + actions */}
      <div className="flex items-center justify-between pt-3 mt-3 border-t border-argus-border/50">
        <div className="flex items-center gap-4 text-xs text-argus-text-dim">
          <span>{doc.word_count.toLocaleString()} words</span>
          <span>{doc.reading_time_min} min read</span>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRead();
            }}
            className="p-1.5 rounded text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2 transition-colors"
            aria-label="Read document"
            title="Read"
          >
            <BookOpen className="w-4 h-4" />
          </button>

          {doc.is_editable && onEdit && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit();
              }}
              className="p-1.5 rounded text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2 transition-colors"
              aria-label="Edit document"
              title="Edit"
            >
              <Pencil className="w-4 h-4" />
            </button>
          )}

          {doc.is_editable && onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-1.5 rounded text-argus-text-dim hover:text-argus-loss hover:bg-argus-loss/10 transition-colors"
              aria-label="Delete document"
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}
