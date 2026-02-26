/**
 * Symbol Detail UI state store using Zustand.
 *
 * Manages the symbol detail slide-out panel state. Used across multiple pages
 * (Dashboard, Pattern Library, Trades) for consistent symbol inspection.
 * Session-level only — does not persist to localStorage.
 */

import { create } from 'zustand';

interface SymbolDetailUIState {
  // Panel state
  selectedSymbol: string | null;
  isOpen: boolean;

  // Actions
  open: (symbol: string) => void;
  close: () => void;
}

export const useSymbolDetailUI = create<SymbolDetailUIState>((set) => ({
  // Initial state
  selectedSymbol: null,
  isOpen: false,

  // Actions
  open: (symbol) => set({ selectedSymbol: symbol, isOpen: true }),
  close: () => set({ isOpen: false, selectedSymbol: null }),
}));
