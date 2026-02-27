/**
 * Journal list view for The Debrief page.
 *
 * Displays:
 * - JournalEntryForm at top (collapsed by default)
 * - Filter row (type, strategy, tag, search)
 * - Entry count
 * - Reverse-chronological list of JournalEntryCards
 * - Delete confirmation modal
 * - Edit form when editing an entry
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Search, X, Pencil, Filter } from 'lucide-react';
import { JournalEntryForm } from './JournalEntryForm';
import { JournalEntryCard } from './JournalEntryCard';
import { DebriefSkeleton } from '../DebriefSkeleton';
import { ConfirmModal } from '../../../components/ConfirmModal';
import { EmptyState } from '../../../components/EmptyState';
import { useDebriefUI } from '../../../stores/debriefUI';
import {
  useJournalEntries,
  useDeleteJournalEntry,
  useJournalTags,
} from '../../../hooks/useJournal';
import { useStrategies } from '../../../hooks/useStrategies';
import type { JournalEntry, JournalEntryType } from '../../../api/types';
import { DURATION, EASE } from '../../../utils/motion';

// Type filter options
const TYPE_OPTIONS: { value: JournalEntryType | ''; label: string }[] = [
  { value: '', label: 'All Types' },
  { value: 'observation', label: 'Observation' },
  { value: 'trade_annotation', label: 'Trade Annotation' },
  { value: 'pattern_note', label: 'Pattern Note' },
  { value: 'system_note', label: 'System Note' },
];

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

export function JournalList() {
  // Zustand state
  const journalFilters = useDebriefUI((s) => s.journalFilters);
  const setJournalFilter = useDebriefUI((s) => s.setJournalFilter);
  const clearJournalFilters = useDebriefUI((s) => s.clearJournalFilters);
  const editingJournalEntryId = useDebriefUI((s) => s.editingJournalEntryId);
  const setEditingJournalEntryId = useDebriefUI((s) => s.setEditingJournalEntryId);

  // Local state
  const [searchInput, setSearchInput] = useState(journalFilters.search);
  const [deletingEntry, setDeletingEntry] = useState<JournalEntry | null>(null);

  // Build API params from filters
  const apiParams = useMemo(() => {
    const params: Record<string, string | undefined> = {};
    if (journalFilters.type) params.entry_type = journalFilters.type;
    if (journalFilters.strategy_id) params.strategy_id = journalFilters.strategy_id;
    if (journalFilters.tag) params.tag = journalFilters.tag;
    if (journalFilters.search) params.search = journalFilters.search;
    return params;
  }, [journalFilters]);

  // Data fetching
  const { data, isLoading, error } = useJournalEntries(apiParams);
  const { data: tagsData } = useJournalTags();
  const { data: strategiesData } = useStrategies();

  // Mutations
  const deleteMutation = useDeleteJournalEntry();

  const strategies = strategiesData?.strategies ?? [];
  const tags = tagsData?.tags ?? [];

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      setJournalFilter('search', searchInput || null);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchInput, setJournalFilter]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return (
      journalFilters.type !== null ||
      journalFilters.strategy_id !== null ||
      journalFilters.tag !== null ||
      journalFilters.search !== ''
    );
  }, [journalFilters]);

  // Handle delete confirmation
  const handleConfirmDelete = useCallback(async () => {
    if (!deletingEntry) return;

    try {
      await deleteMutation.mutateAsync(deletingEntry.id);
      setDeletingEntry(null);
    } catch (error) {
      console.error('Failed to delete journal entry:', error);
    }
  }, [deletingEntry, deleteMutation]);

  // Handle edit cancel (also used for save since card will close edit mode)
  const handleEditCancel = useCallback(() => {
    setEditingJournalEntryId(null);
  }, [setEditingJournalEntryId]);

  // Loading state (only on initial load, not during filter changes)
  if (isLoading && !data) {
    return <DebriefSkeleton section="journal" />;
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-argus-warning mb-2 text-sm">
          Unable to load journal entries
        </p>
        <p className="text-xs text-argus-text-dim">{error.message}</p>
      </div>
    );
  }

  // Sort entries reverse chronologically (newest first)
  const entries = [...(data?.entries ?? [])].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const totalCount = data?.total ?? 0;
  const displayedCount = entries.length;

  return (
    <>
      <div className="space-y-4">
        {/* Entry form at top */}
        <JournalEntryForm />

        {/* Filter row */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Type filter */}
          <select
            value={journalFilters.type ?? ''}
            onChange={(e) => setJournalFilter('type', e.target.value || null)}
            className="text-sm bg-argus-surface-2 border border-argus-border rounded-md px-3 py-2 text-argus-text focus:outline-none focus:border-argus-accent transition-colors"
          >
            {TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Strategy filter */}
          <select
            value={journalFilters.strategy_id ?? ''}
            onChange={(e) => setJournalFilter('strategy_id', e.target.value || null)}
            className="text-sm bg-argus-surface-2 border border-argus-border rounded-md px-3 py-2 text-argus-text focus:outline-none focus:border-argus-accent transition-colors"
          >
            <option value="">All Strategies</option>
            {strategies.map((strategy) => (
              <option key={strategy.strategy_id} value={strategy.strategy_id}>
                {strategy.name}
              </option>
            ))}
          </select>

          {/* Tag filter */}
          <select
            value={journalFilters.tag ?? ''}
            onChange={(e) => setJournalFilter('tag', e.target.value || null)}
            className="text-sm bg-argus-surface-2 border border-argus-border rounded-md px-3 py-2 text-argus-text focus:outline-none focus:border-argus-accent transition-colors"
          >
            <option value="">All Tags</option>
            {tags.map((tag) => (
              <option key={tag} value={tag}>
                {tag}
              </option>
            ))}
          </select>

          {/* Search input */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-argus-text-dim" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search entries..."
              className="w-full text-sm bg-argus-surface-2 border border-argus-border rounded-md pl-9 pr-3 py-2 text-argus-text placeholder:text-argus-text-dim focus:outline-none focus:border-argus-accent transition-colors"
            />
            {searchInput && (
              <button
                onClick={() => setSearchInput('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-argus-text-dim hover:text-argus-text"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Clear filters */}
          {hasActiveFilters && (
            <button
              onClick={() => {
                clearJournalFilters();
                setSearchInput('');
              }}
              className="text-sm text-argus-accent hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Entry count */}
        <div className="text-sm text-argus-text-dim">
          Showing {displayedCount} of {totalCount} {totalCount === 1 ? 'entry' : 'entries'}
        </div>

        {/* Entries list */}
        {entries.length === 0 ? (
          hasActiveFilters ? (
            <EmptyState
              icon={Filter}
              message="No entries match your filters."
              action={
                <button
                  onClick={() => {
                    clearJournalFilters();
                    setSearchInput('');
                  }}
                  className="text-sm text-argus-accent hover:underline"
                >
                  Clear filters
                </button>
              }
            />
          ) : (
            <EmptyState
              icon={Pencil}
              message="No journal entries yet. Start capturing your observations, trade annotations, and pattern notes."
            />
          )
        ) : (
          <div className="space-y-3">
            {entries.map((entry, index) => (
              <motion.div
                key={entry.id}
                custom={index}
                initial="hidden"
                animate="visible"
                variants={listItemVariants}
              >
                <JournalEntryCard
                  entry={entry}
                  isEditing={editingJournalEntryId === entry.id}
                  onEdit={() => setEditingJournalEntryId(entry.id)}
                  onEditCancel={handleEditCancel}
                  onDelete={() => setDeletingEntry(entry)}
                />
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Delete confirmation modal */}
      <ConfirmModal
        isOpen={!!deletingEntry}
        title="Delete Entry"
        message={`Are you sure you want to delete "${deletingEntry?.title || 'this entry'}"? This action cannot be undone.`}
        confirmText="Delete"
        isLoading={deleteMutation.isPending}
        variant="danger"
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeletingEntry(null)}
      />
    </>
  );
}
