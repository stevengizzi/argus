/**
 * Orchestrator UI state store using Zustand.
 *
 * Manages throttle override dialog state for the Orchestrator page.
 * Session-level only — does not persist to localStorage.
 */

import { create } from 'zustand';

interface OrchestratorUIState {
  // Override dialog state
  overrideDialogOpen: boolean;
  overrideTargetStrategy: string | null;

  // Actions
  openOverrideDialog: (strategyId: string) => void;
  closeOverrideDialog: () => void;
}

export const useOrchestratorUI = create<OrchestratorUIState>((set) => ({
  // Initial state
  overrideDialogOpen: false,
  overrideTargetStrategy: null,

  // Actions
  openOverrideDialog: (strategyId) =>
    set({
      overrideDialogOpen: true,
      overrideTargetStrategy: strategyId,
    }),
  closeOverrideDialog: () =>
    set({
      overrideDialogOpen: false,
      overrideTargetStrategy: null,
    }),
}));
