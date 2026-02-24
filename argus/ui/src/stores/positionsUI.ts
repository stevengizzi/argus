/**
 * Positions UI state store using Zustand.
 *
 * Manages display mode (table/timeline) and position filter (all/open/closed).
 * State persists across responsive layout changes (no re-mount reset).
 * Session-level only — does not persist to localStorage.
 */

import { create } from 'zustand';
import { isMarketOpen } from '../utils/marketTime';

export type DisplayMode = 'table' | 'timeline';
export type PositionFilter = 'all' | 'open' | 'closed';

interface PositionsUIState {
  // View state
  displayMode: DisplayMode;
  positionFilter: PositionFilter;

  // Actions
  setDisplayMode: (mode: DisplayMode) => void;
  setPositionFilter: (filter: PositionFilter) => void;
}

/**
 * Get the default position filter based on market status.
 * During market hours: 'open' (focus on active positions)
 * After hours: 'all' (review both open and closed)
 */
function getDefaultPositionFilter(): PositionFilter {
  return isMarketOpen() ? 'open' : 'all';
}

export const usePositionsUIStore = create<PositionsUIState>((set) => ({
  // Initial state
  displayMode: 'table',
  positionFilter: getDefaultPositionFilter(),

  // Actions
  setDisplayMode: (mode) => set({ displayMode: mode }),
  setPositionFilter: (filter) => set({ positionFilter: filter }),
}));
