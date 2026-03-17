/**
 * Observatory page — immersive pipeline visualization.
 *
 * Full-bleed layout (no padding, no card wrappers).
 * Four views: Funnel, Matrix, Timeline, Radar.
 * Keyboard-first interaction with tier/symbol navigation.
 *
 * Sprint 25 — Page 8 in Command Center.
 */

import { useState, useCallback, useRef, lazy, Suspense } from 'react';
import { ObservatoryLayout } from './ObservatoryLayout';
import { ShortcutOverlay } from './ShortcutOverlay';
import { MatrixView } from './views/MatrixView';
import {
  useObservatoryKeyboard,
  type ObservatoryView,
} from './hooks/useObservatoryKeyboard';
import type { FunnelViewHandle } from './views/FunnelView';

const LazyFunnelView = lazy(() =>
  import('./views/FunnelView').then((m) => ({ default: m.FunnelView }))
);

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

  const funnelRef = useRef<FunnelViewHandle>(null);

  // Placeholder symbols — will come from API tier data in later sessions
  const symbols: string[] = [];

  const handleResetCamera = useCallback(() => funnelRef.current?.resetCamera(), []);
  const handleFitView = useCallback(() => funnelRef.current?.fitView(), []);

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
    onResetCamera: handleResetCamera,
    onFitView: handleFitView,
  });

  const handleDeselectSymbol = useCallback(() => setSelectedSymbol(null), []);
  const handleSelectTier = useCallback((index: number) => setSelectedTierIndex(index), []);
  const handleSelectSymbol = useCallback((symbol: string) => setSelectedSymbol(symbol), []);

  function renderView() {
    if (currentView === 'funnel') {
      return (
        <Suspense
          fallback={
            <div className="flex items-center justify-center h-full">
              <p className="text-sm text-argus-text-dim">Loading 3D view…</p>
            </div>
          }
        >
          <LazyFunnelView
            ref={funnelRef}
            selectedTier={selectedTierIndex}
            selectedSymbol={selectedSymbol}
            onSelectSymbol={handleSelectSymbol}
          />
        </Suspense>
      );
    }

    if (currentView === 'matrix') {
      return (
        <MatrixView
          selectedTier={selectedTierIndex}
          selectedSymbol={selectedSymbol}
          onSelectSymbol={handleSelectSymbol}
        />
      );
    }

    // Placeholder for views not yet implemented
    return (
      <div
        className="flex items-center justify-center h-full"
        data-testid={`view-${currentView}`}
      >
        <div className="text-center">
          <p className="text-lg font-semibold text-argus-text" data-testid="active-view-label">
            {VIEW_LABELS[currentView]}
          </p>
          <p className="text-xs text-argus-text-dim mt-1">
            Press F/M/R/T to switch views
          </p>
        </div>
      </div>
    );
  }

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
        {renderView()}
      </ObservatoryLayout>

      {/* Shortcut help overlay */}
      <ShortcutOverlay
        isOpen={shortcutHelpOpen}
        onClose={() => setShortcutHelpOpen(false)}
      />
    </div>
  );
}
