/**
 * Observatory page — immersive pipeline visualization.
 *
 * Full-bleed layout (no padding, no card wrappers).
 * Four views: Funnel, Matrix, Timeline, Radar.
 * Keyboard-first interaction with tier/symbol navigation.
 *
 * Sprint 25 — Page 8 in Command Center.
 */

import { useState, useCallback } from 'react';
import { ObservatoryLayout } from './ObservatoryLayout';
import { ShortcutOverlay } from './ShortcutOverlay';
import {
  useObservatoryKeyboard,
  type ObservatoryView,
} from './hooks/useObservatoryKeyboard';

const VIEW_LABELS: Record<ObservatoryView, string> = {
  funnel: 'Funnel View',
  matrix: 'Matrix View',
  timeline: 'Timeline View',
  radar: 'Radar View',
};

export function ObservatoryPage() {
  const [currentView, setCurrentView] = useState<ObservatoryView>('funnel');
  const [selectedTierIndex, setSelectedTierIndex] = useState(0);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false);

  // Placeholder symbols — will come from API tier data in later sessions
  const symbols: string[] = [];

  useObservatoryKeyboard({
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
  });

  const handleDeselectSymbol = useCallback(() => setSelectedSymbol(null), []);
  const handleSelectTier = useCallback((index: number) => setSelectedTierIndex(index), []);

  return (
    <div
      className="-m-4 md:-m-5 min-[1024px]:-m-6 min-[1024px]:-mt-6 h-[calc(100vh-0px)] min-[1024px]:h-[calc(100vh-0px)]"
      data-testid="observatory-page"
    >
      <ObservatoryLayout
        currentView={currentView}
        selectedTierIndex={selectedTierIndex}
        onSelectTier={handleSelectTier}
        selectedSymbol={selectedSymbol}
        onDeselectSymbol={handleDeselectSymbol}
      >
        {/* View placeholder — replaced with actual views in later sessions */}
        <div
          className="flex items-center justify-center h-full"
          data-testid={`view-${currentView}`}
        >
          <div className="text-center">
            <p className="text-lg font-semibold text-argus-text" data-testid="active-view-label">
              {VIEW_LABELS[currentView]}
            </p>
            <p className="text-xs text-argus-text-dim mt-1">
              Press 1-4 to switch views
            </p>
          </div>
        </div>
      </ObservatoryLayout>

      {/* Shortcut help overlay */}
      <ShortcutOverlay
        isOpen={shortcutHelpOpen}
        onClose={() => setShortcutHelpOpen(false)}
      />
    </div>
  );
}
