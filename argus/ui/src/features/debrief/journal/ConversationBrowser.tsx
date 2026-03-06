/**
 * Learning Journal Conversation Browser.
 *
 * Displays past AI conversations with filtering by date and tag.
 * Supports list view and detail view for reading full conversation history.
 *
 * Sprint 22 Session 6.
 */

import { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  MessageSquare,
  Calendar,
  Filter,
  Sparkles,
  BookOpen,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { Card } from '../../../components/Card';
import { useConversations, useConversation } from '../../../hooks';
import { useCopilotUIStore } from '../../../stores/copilotUI';
import { formatDate, formatRelativeTime } from '../../../utils/format';
import { DURATION, EASE } from '../../../utils/motion';
import type { ConversationSummary, ConversationTag } from '../../../api/types';

/** Tag color mapping */
const TAG_COLORS: Record<ConversationTag, string> = {
  session: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  research: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  debrief: 'bg-green-500/20 text-green-400 border-green-500/30',
  'pre-market': 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  general: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

/** Date filter presets */
type DatePreset = 'today' | 'week' | 'month' | 'all';

const DATE_PRESETS: { label: string; value: DatePreset }[] = [
  { label: 'Today', value: 'today' },
  { label: 'This Week', value: 'week' },
  { label: 'This Month', value: 'month' },
  { label: 'All', value: 'all' },
];

const ALL_TAGS: ConversationTag[] = ['session', 'research', 'debrief', 'pre-market', 'general'];

interface ConversationBrowserProps {
  /** Callback to open the Copilot panel */
  onOpenCopilot?: () => void;
}

/**
 * Tag badge component
 */
function TagBadge({ tag }: { tag: string }) {
  const colorClass = TAG_COLORS[tag as ConversationTag] ?? TAG_COLORS.general;
  return (
    <span
      className={`px-2 py-0.5 text-xs font-medium rounded border ${colorClass}`}
    >
      {tag}
    </span>
  );
}

/**
 * Skeleton for conversation list item
 */
function ConversationItemSkeleton() {
  return (
    <div className="p-4 border-b border-argus-border animate-pulse">
      <div className="flex items-start justify-between mb-2">
        <div className="h-4 w-20 bg-argus-surface-2 rounded" />
        <div className="h-5 w-16 bg-argus-surface-2 rounded" />
      </div>
      <div className="h-4 w-3/4 bg-argus-surface-2 rounded mb-2" />
      <div className="h-3 w-24 bg-argus-surface-2 rounded" />
    </div>
  );
}

/**
 * Empty state when no conversations exist
 */
function EmptyState({ onOpenCopilot }: { onOpenCopilot?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <BookOpen className="w-12 h-12 text-argus-text-dim mb-4" />
      <h3 className="text-lg font-medium text-argus-text mb-2">
        No conversations yet
      </h3>
      <p className="text-sm text-argus-text-dim mb-4 max-w-sm">
        Start chatting with the Copilot to build your Learning Journal.
        Your conversations will appear here for future reference.
      </p>
      {onOpenCopilot && (
        <button
          onClick={onOpenCopilot}
          className="flex items-center gap-2 px-4 py-2 bg-argus-accent/20 text-argus-accent rounded-lg hover:bg-argus-accent/30 transition-colors"
        >
          <Sparkles className="w-4 h-4" />
          Open Copilot
        </button>
      )}
    </div>
  );
}

/**
 * Conversation list item
 */
function ConversationItem({
  conversation,
  onClick,
}: {
  conversation: ConversationSummary;
  onClick: () => void;
}) {
  const createdAt = new Date(conversation.created_at);
  const title = conversation.title || 'Untitled conversation';

  return (
    <button
      onClick={onClick}
      className="w-full p-4 text-left border-b border-argus-border hover:bg-argus-surface-2 transition-colors"
    >
      <div className="flex items-start justify-between mb-1">
        <span className="text-xs text-argus-text-dim">
          {formatDate(conversation.date)}
        </span>
        <TagBadge tag={conversation.tag} />
      </div>
      <h4 className="text-sm font-medium text-argus-text mb-1 line-clamp-2">
        {title}
      </h4>
      <div className="flex items-center gap-3 text-xs text-argus-text-dim">
        <span className="flex items-center gap-1">
          <MessageSquare className="w-3 h-3" />
          {conversation.message_count} messages
        </span>
        <span>{formatRelativeTime(createdAt)}</span>
      </div>
    </button>
  );
}

/**
 * Filter bar component
 */
function FilterBar({
  datePreset,
  setDatePreset,
  selectedTags,
  toggleTag,
}: {
  datePreset: DatePreset;
  setDatePreset: (preset: DatePreset) => void;
  selectedTags: ConversationTag[];
  toggleTag: (tag: ConversationTag) => void;
}) {
  const [showTagFilter, setShowTagFilter] = useState(false);

  return (
    <div className="p-3 border-b border-argus-border space-y-2">
      {/* Date presets */}
      <div className="flex items-center gap-2">
        <Calendar className="w-4 h-4 text-argus-text-dim" />
        <div className="flex gap-1">
          {DATE_PRESETS.map((preset) => (
            <button
              key={preset.value}
              onClick={() => setDatePreset(preset.value)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                datePreset === preset.value
                  ? 'bg-argus-accent/20 text-argus-accent'
                  : 'text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2'
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tag filter toggle */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setShowTagFilter(!showTagFilter)}
          className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors ${
            selectedTags.length > 0
              ? 'bg-argus-accent/20 text-argus-accent'
              : 'text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2'
          }`}
        >
          <Filter className="w-3 h-3" />
          Tags {selectedTags.length > 0 && `(${selectedTags.length})`}
        </button>
      </div>

      {/* Tag filter options */}
      <AnimatePresence>
        {showTagFilter && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: DURATION.fast }}
            className="flex flex-wrap gap-1.5 overflow-hidden"
          >
            {ALL_TAGS.map((tag) => (
              <button
                key={tag}
                onClick={() => toggleTag(tag)}
                className={`px-2 py-1 text-xs rounded border transition-colors ${
                  selectedTags.includes(tag)
                    ? TAG_COLORS[tag]
                    : 'border-argus-border text-argus-text-dim hover:border-argus-text-dim'
                }`}
              >
                {tag}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Conversation detail view - shows full message history
 */
function ConversationDetail({
  conversationId,
  onBack,
}: {
  conversationId: string;
  onBack: () => void;
}) {
  const { data, isLoading, error } = useConversation(conversationId);

  if (isLoading) {
    return (
      <div className="animate-pulse p-4 space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className={`flex ${i % 2 === 0 ? 'justify-end' : 'justify-start'}`}>
            <div className="w-3/4 space-y-2">
              <div className="h-4 bg-argus-surface-2 rounded w-full" />
              <div className="h-4 bg-argus-surface-2 rounded w-5/6" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-argus-loss">Failed to load conversation</p>
        <button
          onClick={onBack}
          className="mt-2 text-sm text-argus-accent hover:text-argus-accent-bright"
        >
          Go back
        </button>
      </div>
    );
  }

  const { conversation, messages } = data;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-argus-border flex items-center gap-3">
        <button
          onClick={onBack}
          className="p-1.5 rounded hover:bg-argus-surface-2 text-argus-text-dim hover:text-argus-text transition-colors"
          aria-label="Back to list"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-argus-text truncate">
            {conversation.title || 'Untitled conversation'}
          </h3>
          <div className="flex items-center gap-2 text-xs text-argus-text-dim">
            <span>{formatDate(conversation.date)}</span>
            <TagBadge tag={conversation.tag} />
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2 ${
                message.role === 'user'
                  ? 'bg-argus-accent/20 text-argus-text rounded-br-md'
                  : 'bg-argus-surface-2 text-argus-text rounded-bl-md'
              }`}
            >
              {message.role === 'user' ? (
                <p className="text-sm whitespace-pre-wrap break-words">
                  {message.content}
                </p>
              ) : (
                <div className="prose prose-sm prose-invert max-w-none text-sm">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeSanitize]}
                    components={{
                      p: ({ children }) => (
                        <p className="my-1 leading-relaxed">{children}</p>
                      ),
                      code: ({ children }) => (
                        <code className="px-1 py-0.5 bg-argus-bg rounded text-argus-accent font-mono text-xs">
                          {children}
                        </code>
                      ),
                      ul: ({ children }) => (
                        <ul className="my-1 ml-4 list-disc space-y-0.5">
                          {children}
                        </ul>
                      ),
                      ol: ({ children }) => (
                        <ol className="my-1 ml-4 list-decimal space-y-0.5">
                          {children}
                        </ol>
                      ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Main ConversationBrowser component
 */
export function ConversationBrowser({ onOpenCopilot }: ConversationBrowserProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [datePreset, setDatePreset] = useState<DatePreset>('all');
  const [selectedTags, setSelectedTags] = useState<ConversationTag[]>([]);
  const [offset, setOffset] = useState(0);
  const limit = 20;

  // Use copilot store to open the panel
  const openCopilot = useCopilotUIStore((state) => state.open);

  // Calculate date range from preset
  const dateFilters = useMemo(() => {
    const now = new Date();
    const today = now.toISOString().split('T')[0];

    switch (datePreset) {
      case 'today':
        return { dateFrom: today, dateTo: today };
      case 'week': {
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        return { dateFrom: weekAgo.toISOString().split('T')[0], dateTo: today };
      }
      case 'month': {
        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        return { dateFrom: monthAgo.toISOString().split('T')[0], dateTo: today };
      }
      default:
        return {};
    }
  }, [datePreset]);

  const { data, isLoading, error } = useConversations({
    ...dateFilters,
    tags: selectedTags.length > 0 ? selectedTags : undefined,
    limit,
    offset,
  });

  const handleToggleTag = useCallback((tag: ConversationTag) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
    setOffset(0); // Reset pagination on filter change
  }, []);

  const handleLoadMore = useCallback(() => {
    setOffset((prev) => prev + limit);
  }, [limit]);

  const handleOpenCopilot = useCallback(() => {
    if (onOpenCopilot) {
      onOpenCopilot();
    } else {
      openCopilot();
    }
  }, [onOpenCopilot, openCopilot]);

  // Show detail view if a conversation is selected
  if (selectedId) {
    return (
      <Card className="h-full overflow-hidden">
        <ConversationDetail
          conversationId={selectedId}
          onBack={() => setSelectedId(null)}
        />
      </Card>
    );
  }

  // List view
  return (
    <Card className="h-full overflow-hidden flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-argus-border">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-argus-accent" />
          <h3 className="text-sm font-medium text-argus-text uppercase tracking-wider">
            Learning Journal
          </h3>
        </div>
        <p className="text-xs text-argus-text-dim mt-1">
          Browse your AI Copilot conversations
        </p>
      </div>

      {/* Filters */}
      <FilterBar
        datePreset={datePreset}
        setDatePreset={(preset) => {
          setDatePreset(preset);
          setOffset(0);
        }}
        selectedTags={selectedTags}
        toggleTag={handleToggleTag}
      />

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && offset === 0 ? (
          // Initial loading state
          <>
            <ConversationItemSkeleton />
            <ConversationItemSkeleton />
            <ConversationItemSkeleton />
          </>
        ) : error ? (
          <div className="p-4 text-center text-sm text-argus-loss">
            Failed to load conversations
          </div>
        ) : !data || data.conversations.length === 0 ? (
          <EmptyState onOpenCopilot={handleOpenCopilot} />
        ) : (
          <>
            {data.conversations.map((conv) => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                onClick={() => setSelectedId(conv.id)}
              />
            ))}

            {/* Load more button */}
            {data.conversations.length >= limit && data.total > offset + limit && (
              <button
                onClick={handleLoadMore}
                className="w-full p-3 text-sm text-argus-accent hover:bg-argus-surface-2 transition-colors"
                disabled={isLoading}
              >
                {isLoading ? 'Loading...' : 'Load more'}
              </button>
            )}
          </>
        )}
      </div>
    </Card>
  );
}
