/**
 * Keyboard shortcut system for the Observatory page.
 *
 * Handles all Observatory-specific keyboard navigation:
 * - 1-4: Switch between views (funnel, matrix, timeline, radar)
 * - [/]: Navigate tiers up/down
 * - Tab/Shift+Tab: Cycle symbols within current tier
 * - Enter: Confirm selection / open detail panel
 * - Escape: Deselect symbol / close detail panel
 * - /: Open symbol search overlay
 * - ?: Toggle shortcut help overlay
 * - r/R: Reset camera (future Three.js)
 * - f/F: Fit view (future Three.js)
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
  '1': 'funnel',
  '2': 'matrix',
  '3': 'timeline',
  '4': 'radar',
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

      // View switching: 1-4
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
      if (e.key === 'Tab') {
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

      // Camera controls (no-op for now)
      if (e.key === 'r' || e.key === 'R') {
        // Reset camera — wired in Three.js sessions
        return;
      }
      if (e.key === 'f' || e.key === 'F') {
        // Fit view — wired in Three.js sessions
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
  ]);
}

export { PIPELINE_TIERS };
