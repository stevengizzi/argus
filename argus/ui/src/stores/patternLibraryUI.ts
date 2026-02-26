/**
 * Pattern Library UI state store using Zustand.
 *
 * Manages selected strategy, active tab, filters, and sort order for the
 * Pattern Library page. Session-level only — does not persist to localStorage.
 */

import { create } from 'zustand';

export type FilterKey = 'stage' | 'family' | 'timeWindow';

interface PatternLibraryUIState {
  // Selection state
  selectedStrategyId: string | null;
  activeTab: string;

  // Filters
  filters: {
    stage: string | null;
    family: string | null;
    timeWindow: string | null;
  };

  // Sort
  sortBy: string;

  // Actions
  setSelectedStrategy: (id: string | null) => void;
  setActiveTab: (tab: string) => void;
  setFilter: (key: FilterKey, value: string | null) => void;
  setSortBy: (sort: string) => void;
  clearFilters: () => void;
}

export const usePatternLibraryUI = create<PatternLibraryUIState>((set) => ({
  // Initial state
  selectedStrategyId: null,
  activeTab: 'overview',
  filters: { stage: null, family: null, timeWindow: null },
  sortBy: 'name',

  // Actions
  setSelectedStrategy: (id) => set({ selectedStrategyId: id }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setFilter: (key, value) =>
    set((state) => ({
      filters: { ...state.filters, [key]: value },
    })),
  setSortBy: (sort) => set({ sortBy: sort }),
  clearFilters: () =>
    set({
      filters: { stage: null, family: null, timeWindow: null },
    }),
}));
