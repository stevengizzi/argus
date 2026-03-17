/**
 * Keyboard shortcut system for the Observatory page.
 *
 * Handles all Observatory-specific keyboard navigation:
 * - f/m/r/t: Switch between views (funnel, matrix, radar, timeline)
 * - [/]: Navigate tiers up/down
 * - Tab/Shift+Tab: Cycle symbols within current tier
 * - Enter: Confirm selection / open detail panel
 * - Escape: Deselect symbol / close detail panel
 * - /: Open symbol search overlay
 * - ?: Toggle shortcut help overlay
 *
 * Only active when Observatory page is focused (not when typing in inputs).
 */

import { useEffect, useCallback } from 'react';

export type ObservatoryView = 'funnel' | 'matrix' | 'timeline' | 'radar';

const PIPELINE_TIERS = [
  'Universe',
  'Viable',
  'Routed',
  'Evaluating',
  'Near-trigger',
  'Signal',
  'Traded',
] as const;

export type PipelineTier = (typeof PIPELINE_TIERS)[number];

const VIEW_KEYS: Record<string, ObservatoryView> = {
  'f': 'funnel',
  'm': 'matrix',
  'r': 'radar',
  't': 'timeline',
};

interface ObservatoryKeyboardState {
  currentView: ObservatoryView;
  setCurrentView: (view: ObservatoryView) => void;
  selectedTierIndex: number;
  setSelectedTierIndex: (index: number) => void;
  selectedSymbol: string | null;
  setSelectedSymbol: (symbol: string | null) => void;
  symbols: string[];
  searchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  shortcutHelpOpen: boolean;
  setShortcutHelpOpen: (open: boolean) => void;
  onResetCamera?: () => void;
  onFitView?: () => void;
  /** When true, Matrix view owns Tab handling — skip page-level Tab cycle. */
  isMatrixActive?: boolean;
}

export function useObservatoryKeyboard({
  currentView,
  setCurrentView,
  selectedTierIndex,
  setSelectedTierIndex,
  selectedSymbol,
  setSelectedSymbol,
  symbols,
  searchOpen,
  setSearchOpen,
  shortcutHelpOpen,
  setShortcutHelpOpen,
  onResetCamera,
  onFitView,
  isMatrixActive,
}: ObservatoryKeyboardState): void {
  const handleTierNav = useCallback(
    (direction: -1 | 1) => {
      setSelectedTierIndex(
        Math.max(0, Math.min(PIPELINE_TIERS.length - 1, selectedTierIndex + direction))
      );
    },
    [selectedTierIndex, setSelectedTierIndex]
  );

  const handleSymbolCycle = useCallback(
    (direction: -1 | 1) => {
      if (symbols.length === 0) return;

      if (selectedSymbol === null) {
        setSelectedSymbol(symbols[0]);
        return;
      }

      const currentIndex = symbols.indexOf(selectedSymbol);
      if (currentIndex === -1) {
        setSelectedSymbol(symbols[0]);
        return;
      }

      const nextIndex = (currentIndex + direction + symbols.length) % symbols.length;
      setSelectedSymbol(symbols[nextIndex]);
    },
    [symbols, selectedSymbol, setSelectedSymbol]
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Skip when typing in inputs, textareas, or contenteditable
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      // Skip when modifier keys are held (except Shift for Shift+Tab)
      const hasModifier = e.metaKey || e.ctrlKey || e.altKey;
      if (hasModifier) return;

      // View switching: f/m/r/t
      const view = VIEW_KEYS[e.key];
      if (view) {
        setCurrentView(view);
        return;
      }

      // Tier navigation: [ and ]
      if (e.key === '[') {
        handleTierNav(-1);
        return;
      }
      if (e.key === ']') {
        handleTierNav(1);
        return;
      }

      // Symbol cycling: Tab / Shift+Tab
      // When Matrix is active, MatrixView owns Tab (syncs highlight + selection)
      if (e.key === 'Tab' && !isMatrixActive) {
        e.preventDefault();
        handleSymbolCycle(e.shiftKey ? -1 : 1);
        return;
      }

      // Confirm selection: Enter
      if (e.key === 'Enter') {
        // If no symbol selected, select first in tier
        if (selectedSymbol === null && symbols.length > 0) {
          setSelectedSymbol(symbols[0]);
        }
        return;
      }

      // Deselect / close: Escape
      if (e.key === 'Escape') {
        if (shortcutHelpOpen) {
          setShortcutHelpOpen(false);
          return;
        }
        if (searchOpen) {
          setSearchOpen(false);
          return;
        }
        if (selectedSymbol !== null) {
          setSelectedSymbol(null);
          return;
        }
        return;
      }

      // Symbol search: /
      if (e.key === '/') {
        e.preventDefault();
        setSearchOpen(!searchOpen);
        return;
      }

      // Shortcut help: ?
      if (e.key === '?') {
        setShortcutHelpOpen(!shortcutHelpOpen);
        return;
      }

      // Camera controls (Shift+R / Shift+F) — only in funnel/radar views.
      // Ordering note: this check runs AFTER the lowercase VIEW_KEYS lookup
      // above. When Shift is held, e.key is uppercase ('R'/'F'), so the
      // VIEW_KEYS match for 'r'/'f' won't fire — they are case-sensitive.
      // This means Shift+R and Shift+F safely reach here without triggering
      // a view switch.
      const is3dView = currentView === 'funnel' || currentView === 'radar';
      if (is3dView && e.key === 'R' && e.shiftKey) {
        onResetCamera?.();
        return;
      }
      if (is3dView && e.key === 'F' && e.shiftKey) {
        onFitView?.();
        return;
      }

    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    currentView,
    setCurrentView,
    selectedTierIndex,
    handleTierNav,
    selectedSymbol,
    setSelectedSymbol,
    symbols,
    handleSymbolCycle,
    searchOpen,
    setSearchOpen,
    shortcutHelpOpen,
    setShortcutHelpOpen,
    onResetCamera,
    onFitView,
    isMatrixActive,
  ]);
}

export { PIPELINE_TIERS };
