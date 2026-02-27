/**
 * Briefings list view for The Debrief page.
 *
 * Displays a reverse-chronological list of briefings with:
 * - "New Briefing" dropdown button (Pre-Market / End of Day)
 * - BriefingCard components for each briefing
 * - DocumentModal for reading briefings
 * - BriefingEditor when editing
 * - ConfirmModal for delete confirmation
 */

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, ChevronDown, BookOpen } from 'lucide-react';
import { BriefingCard } from './BriefingCard';
import { BriefingEditor } from './BriefingEditor';
import { DebriefSkeleton } from '../DebriefSkeleton';
import { DocumentModal } from '../../../components/DocumentModal';
import { ConfirmModal } from '../../../components/ConfirmModal';
import { EmptyState } from '../../../components/EmptyState';
import { useDebriefUI } from '../../../stores/debriefUI';
import {
  useBriefings,
  useBriefing,
  useCreateBriefing,
  useDeleteBriefing,
} from '../../../hooks/useBriefings';
import type { Briefing } from '../../../api/types';
import { DURATION, EASE } from '../../../utils/motion';

// Animation variants for list items
const listItemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.05,
      duration: DURATION.normal,
      ease: EASE.out,
    },
  }),
};

export function BriefingList() {
  // Zustand state
  const editingBriefingId = useDebriefUI((s) => s.editingBriefingId);
  const setEditingBriefingId = useDebriefUI((s) => s.setEditingBriefingId);
  const readingBriefingId = useDebriefUI((s) => s.readingBriefingId);
  const setReadingBriefingId = useDebriefUI((s) => s.setReadingBriefingId);

  // Data fetching
  const { data, isLoading, error } = useBriefings();
  const { data: readingBriefing } = useBriefing(readingBriefingId);

  // Mutations
  const createMutation = useCreateBriefing();
  const deleteMutation = useDeleteBriefing();

  // Local state
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [deletingBriefing, setDeletingBriefing] = useState<Briefing | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle creating a new briefing
  const handleCreateBriefing = async (type: 'pre_market' | 'eod') => {
    setDropdownOpen(false);

    try {
      const today = new Date().toISOString().split('T')[0];
      const newBriefing = await createMutation.mutateAsync({
        date: today,
        briefing_type: type,
      });
      // Open the editor for the new briefing
      setEditingBriefingId(newBriefing.id);
    } catch (error) {
      // Error is handled by mutation state
      console.error('Failed to create briefing:', error);
    }
  };

  // Handle delete confirmation
  const handleConfirmDelete = async () => {
    if (!deletingBriefing) return;

    try {
      await deleteMutation.mutateAsync(deletingBriefing.id);
      setDeletingBriefing(null);
    } catch (error) {
      console.error('Failed to delete briefing:', error);
    }
  };

  // Handle editor close
  const handleEditorClose = () => {
    setEditingBriefingId(null);
  };

  // If editing, show editor instead of list
  if (editingBriefingId) {
    return (
      <BriefingEditor
        briefingId={editingBriefingId}
        onClose={handleEditorClose}
      />
    );
  }

  // Loading state (only on initial load, not during refetches)
  if (isLoading && !data) {
    return <DebriefSkeleton section="briefings" />;
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-argus-warning mb-2 text-sm">
          Unable to load briefings
        </p>
        <p className="text-xs text-argus-text-dim">{error.message}</p>
      </div>
    );
  }

  // Sort briefings reverse chronologically (newest first)
  const briefings = [...(data?.briefings ?? [])].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );

  // Adapt briefing for DocumentModal (which expects StrategyDocument shape)
  const documentForModal = readingBriefing
    ? {
        doc_id: readingBriefing.id,
        title: readingBriefing.title,
        filename: '', // Not used
        word_count: readingBriefing.word_count,
        reading_time_min: readingBriefing.reading_time_min,
        last_modified: readingBriefing.updated_at,
        content: readingBriefing.content,
      }
    : null;

  return (
    <>
      <div className="space-y-4">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-argus-text-dim">
            {briefings.length > 0
              ? `${briefings.length} briefing${briefings.length !== 1 ? 's' : ''}`
              : 'Briefings'}
          </h3>

          {/* New Briefing dropdown */}
          <div ref={dropdownRef} className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              disabled={createMutation.isPending}
              className="flex items-center gap-2 px-3 py-2 text-sm rounded-md bg-argus-accent hover:bg-argus-accent/80 text-white font-medium transition-colors disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              <span>New Briefing</span>
              <ChevronDown
                className={`w-4 h-4 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {/* Dropdown menu */}
            <AnimatePresence>
              {dropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.95 }}
                  transition={{ duration: DURATION.fast }}
                  className="absolute right-0 mt-2 w-56 py-1 bg-argus-surface border border-argus-border rounded-lg shadow-xl z-10"
                >
                  <button
                    onClick={() => handleCreateBriefing('pre_market')}
                    className="w-full px-4 py-2 text-sm text-left text-argus-text hover:bg-argus-surface-2 transition-colors"
                  >
                    Pre-Market Briefing
                  </button>
                  <button
                    onClick={() => handleCreateBriefing('eod')}
                    className="w-full px-4 py-2 text-sm text-left text-argus-text hover:bg-argus-surface-2 transition-colors"
                  >
                    End of Day Review
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Briefings list */}
        {briefings.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            message="No briefings yet. Create your first one!"
            action={
              <button
                onClick={() => setDropdownOpen(true)}
                className="text-sm text-argus-accent hover:underline"
              >
                Create a briefing
              </button>
            }
          />
        ) : (
          <div className="space-y-3">
            {briefings.map((briefing, index) => (
              <motion.div
                key={briefing.id}
                custom={index}
                initial="hidden"
                animate="visible"
                variants={listItemVariants}
              >
                <BriefingCard
                  briefing={briefing}
                  onRead={() => setReadingBriefingId(briefing.id)}
                  onEdit={() => setEditingBriefingId(briefing.id)}
                  onDelete={() => setDeletingBriefing(briefing)}
                />
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Document modal for reading */}
      <DocumentModal
        document={documentForModal}
        isOpen={!!readingBriefingId && !!readingBriefing}
        onClose={() => setReadingBriefingId(null)}
      />

      {/* Delete confirmation modal */}
      <ConfirmModal
        isOpen={!!deletingBriefing}
        title="Delete Briefing"
        message={`Are you sure you want to delete "${deletingBriefing?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        isLoading={deleteMutation.isPending}
        variant="danger"
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeletingBriefing(null)}
      />
    </>
  );
}
