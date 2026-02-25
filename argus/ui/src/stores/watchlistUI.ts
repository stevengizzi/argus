/**
 * Watchlist sidebar UI state store using Zustand.
 *
 * Manages:
 * - Sidebar collapsed state (desktop)
 * - Mobile overlay open state
 * - Session-level only — does not persist to localStorage.
 */

import { create } from 'zustand';

interface WatchlistUIState {
  // Desktop sidebar collapsed state
  isCollapsed: boolean;
  // Mobile/tablet overlay open state
  isMobileOpen: boolean;

  // Actions
  setCollapsed: (collapsed: boolean) => void;
  toggleCollapsed: () => void;
  setMobileOpen: (open: boolean) => void;
  toggleMobileOpen: () => void;
}

export const useWatchlistUIStore = create<WatchlistUIState>((set) => ({
  // Initial state - expanded on desktop by default
  isCollapsed: false,
  isMobileOpen: false,

  // Actions
  setCollapsed: (collapsed) => set({ isCollapsed: collapsed }),
  toggleCollapsed: () => set((state) => ({ isCollapsed: !state.isCollapsed })),
  setMobileOpen: (open) => set({ isMobileOpen: open }),
  toggleMobileOpen: () => set((state) => ({ isMobileOpen: !state.isMobileOpen })),
}));
