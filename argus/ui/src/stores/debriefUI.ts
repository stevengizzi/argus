/**
 * Debrief UI state store using Zustand.
 *
 * Manages active section, editing states, filters, and other UI state
 * for The Debrief page. Session-level only — does not persist to localStorage.
 *
 * Sprint 22 Session 6: Added 'learning_journal' section.
 */

import { create } from 'zustand';

export type DebriefSection = 'intelligence_brief' | 'briefings' | 'quality' | 'research' | 'journal' | 'learning_journal';

export type JournalFilterKey = 'type' | 'strategy_id' | 'tag' | 'search';

interface JournalFilters {
  type: string | null;
  strategy_id: string | null;
  tag: string | null;
  search: string;
}

interface DebriefUIState {
  // Active tab section
  activeSection: DebriefSection;
  setActiveSection: (section: DebriefSection) => void;

  // Briefings state
  editingBriefingId: string | null;
  setEditingBriefingId: (id: string | null) => void;
  readingBriefingId: string | null;
  setReadingBriefingId: (id: string | null) => void;

  // Research state
  researchCategoryFilter: string | null;
  setResearchCategoryFilter: (category: string | null) => void;
  editingDocumentId: string | null;
  setEditingDocumentId: (id: string | null) => void;
  readingDocumentId: string | null;
  setReadingDocumentId: (id: string | null) => void;

  // Journal state
  journalDraftExpanded: boolean;
  setJournalDraftExpanded: (expanded: boolean) => void;
  editingJournalEntryId: string | null;
  setEditingJournalEntryId: (id: string | null) => void;
  journalFilters: JournalFilters;
  setJournalFilter: (key: JournalFilterKey, value: string | null) => void;
  clearJournalFilters: () => void;
}

const initialJournalFilters: JournalFilters = {
  type: null,
  strategy_id: null,
  tag: null,
  search: '',
};

export const useDebriefUI = create<DebriefUIState>((set) => ({
  // Initial state
  activeSection: 'briefings',
  editingBriefingId: null,
  readingBriefingId: null,
  researchCategoryFilter: null,
  editingDocumentId: null,
  readingDocumentId: null,
  journalDraftExpanded: false,
  editingJournalEntryId: null,
  journalFilters: initialJournalFilters,

  // Actions
  setActiveSection: (section) => set({ activeSection: section }),

  setEditingBriefingId: (id) => set({ editingBriefingId: id }),
  setReadingBriefingId: (id) => set({ readingBriefingId: id }),

  setResearchCategoryFilter: (category) => set({ researchCategoryFilter: category }),
  setEditingDocumentId: (id) => set({ editingDocumentId: id }),
  setReadingDocumentId: (id) => set({ readingDocumentId: id }),

  setJournalDraftExpanded: (expanded) => set({ journalDraftExpanded: expanded }),
  setEditingJournalEntryId: (id) => set({ editingJournalEntryId: id }),

  setJournalFilter: (key, value) =>
    set((state) => ({
      journalFilters: { ...state.journalFilters, [key]: value },
    })),

  clearJournalFilters: () => set({ journalFilters: initialJournalFilters }),
}));
