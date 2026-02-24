/**
 * Capital Allocation UI state store using Zustand.
 *
 * Manages the view mode for the CapitalAllocation component (donut/bars).
 * State persists across page navigations (session-level).
 * Does not persist to localStorage — resets on app refresh.
 *
 * DEC-129 pattern: mirrors positionsUI.ts approach.
 */

import { create } from 'zustand';

export type AllocationViewMode = 'donut' | 'bars';

interface CapitalAllocationUIState {
  // View state
  viewMode: AllocationViewMode;

  // Actions
  setViewMode: (mode: AllocationViewMode) => void;
}

export const useCapitalAllocationUIStore = create<CapitalAllocationUIState>((set) => ({
  // Initial state: default to donut view
  viewMode: 'donut',

  // Actions
  setViewMode: (mode) => set({ viewMode: mode }),
}));
