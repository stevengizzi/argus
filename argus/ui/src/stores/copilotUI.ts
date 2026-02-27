/**
 * AI Copilot panel UI state store using Zustand.
 *
 * Manages:
 * - Panel open/close state
 * - Session-level only — does not persist to localStorage.
 *
 * Sprint 21d — Copilot shell. Panel content activates Sprint 22.
 */

import { create } from 'zustand';

interface CopilotUIState {
  isOpen: boolean;
  toggle: () => void;
  open: () => void;
  close: () => void;
}

export const useCopilotUIStore = create<CopilotUIState>((set) => ({
  isOpen: false,
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
}));
