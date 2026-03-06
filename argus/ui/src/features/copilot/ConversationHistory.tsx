/**
 * Conversation history dropdown for the AI Copilot.
 *
 * Shows previous conversations with pagination and date filtering.
 * Clicking a conversation loads its messages.
 *
 * Sprint 22, Session 4b.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { ChevronDown, Calendar, MessageSquare, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCopilotUIStore } from '../../stores/copilotUI';
import { fetchConversations, loadConversation, type ConversationSummary } from './api';

const CONVERSATIONS_PER_PAGE = 20;

/**
 * Format date for display.
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (date.toDateString() === today.toDateString()) {
    return 'Today';
  }
  if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  }
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined,
  });
}

export function ConversationHistory() {
  const [isOpen, setIsOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentConversationId = useCopilotUIStore((state) => state.conversationId);
  const setIsLoading_ = useCopilotUIStore((state) => state.setIsLoading);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Load conversations when dropdown opens
  const handleToggle = useCallback(async () => {
    const newIsOpen = !isOpen;
    setIsOpen(newIsOpen);

    if (newIsOpen && conversations.length === 0) {
      setIsLoading(true);
      try {
        const response = await fetchConversations({
          limit: CONVERSATIONS_PER_PAGE,
          offset: 0,
        });
        setConversations(response.conversations);
        setHasMore(response.conversations.length === CONVERSATIONS_PER_PAGE);
        setOffset(CONVERSATIONS_PER_PAGE);
      } catch (error) {
        console.error('Failed to load conversations:', error);
      } finally {
        setIsLoading(false);
      }
    }
  }, [isOpen, conversations.length]);

  // Load more conversations
  const handleLoadMore = useCallback(async () => {
    if (isLoading || !hasMore) return;

    setIsLoading(true);
    try {
      const response = await fetchConversations({
        limit: CONVERSATIONS_PER_PAGE,
        offset,
      });
      setConversations((prev) => [...prev, ...response.conversations]);
      setHasMore(response.conversations.length === CONVERSATIONS_PER_PAGE);
      setOffset((prev) => prev + CONVERSATIONS_PER_PAGE);
    } catch (error) {
      console.error('Failed to load more conversations:', error);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, hasMore, offset]);

  // Select a conversation
  const handleSelectConversation = useCallback(
    async (conversation: ConversationSummary) => {
      setIsOpen(false);

      // Skip if already selected
      if (conversation.id === currentConversationId) return;

      setIsLoading_(true);
      try {
        await loadConversation(conversation.id);
      } catch (error) {
        console.error('Failed to load conversation:', error);
      }
    },
    [currentConversationId, setIsLoading_]
  );

  return (
    <div ref={dropdownRef} className="relative">
      {/* Toggle button */}
      <button
        onClick={handleToggle}
        className="flex items-center gap-2 px-3 py-1.5 text-xs text-argus-text-dim hover:text-argus-text bg-argus-surface-2 hover:bg-argus-surface-2/80 rounded-md transition-colors"
        aria-label="Previous conversations"
        aria-expanded={isOpen}
      >
        <Calendar className="w-3.5 h-3.5" />
        <span>Previous</span>
        <ChevronDown
          className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 mt-1 w-64 max-h-80 overflow-hidden bg-argus-surface border border-argus-border rounded-lg shadow-lg z-10"
          >
            {/* Header */}
            <div className="px-3 py-2 border-b border-argus-border">
              <h4 className="text-xs font-medium text-argus-text">Conversations</h4>
            </div>

            {/* Conversation list */}
            <div className="overflow-y-auto max-h-60">
              {isLoading && conversations.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 text-argus-text-dim animate-spin" />
                </div>
              ) : conversations.length === 0 ? (
                <div className="px-3 py-4 text-center text-xs text-argus-text-dim">
                  No previous conversations
                </div>
              ) : (
                <>
                  {conversations.map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => handleSelectConversation(conv)}
                      className={`w-full text-left px-3 py-2 hover:bg-argus-surface-2 transition-colors ${
                        conv.id === currentConversationId
                          ? 'bg-argus-accent/10 border-l-2 border-argus-accent'
                          : ''
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <MessageSquare className="w-3.5 h-3.5 text-argus-text-dim flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-argus-text truncate">
                            {conv.title || `Conversation on ${formatDate(conv.date)}`}
                          </p>
                          <p className="text-[10px] text-argus-text-dim">
                            {formatDate(conv.date)} • {conv.message_count} messages
                          </p>
                        </div>
                      </div>
                    </button>
                  ))}

                  {/* Load more button */}
                  {hasMore && (
                    <button
                      onClick={handleLoadMore}
                      disabled={isLoading}
                      className="w-full px-3 py-2 text-xs text-argus-accent hover:bg-argus-surface-2 transition-colors disabled:opacity-50"
                    >
                      {isLoading ? (
                        <span className="flex items-center justify-center gap-2">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Loading...
                        </span>
                      ) : (
                        'Load more'
                      )}
                    </button>
                  )}
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
