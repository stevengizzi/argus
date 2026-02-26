/**
 * Pattern Library page - strategy documentation and analysis hub.
 *
 * Master-detail layout:
 * - Desktop (>=1024px): Left panel 35%, right panel 65%, side by side
 * - Tablet/Mobile (<1024px): Full-width card list, selecting shows detail view
 *
 * Keyboard shortcuts:
 * - ↓: Select next strategy
 * - ↑: Select previous strategy
 * - Escape: Deselect (close detail panel)
 * - ←: Previous tab (when detail open)
 * - →: Next tab (when detail open)
 */

import { useEffect, useCallback } from 'react';
import { BookOpen } from 'lucide-react';
import { AnimatedPage } from '../components/AnimatedPage';
import { Card } from '../components/Card';
import { Skeleton } from '../components/Skeleton';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { useStrategies } from '../hooks/useStrategies';
import { useSortedStrategies } from '../hooks/useSortedStrategies';
import { usePatternLibraryUI } from '../stores/patternLibraryUI';
import { IncubatorPipeline } from '../features/patterns/IncubatorPipeline';
import { PatternCardGrid } from '../features/patterns/PatternCardGrid';
import { PatternDetail } from '../features/patterns/PatternDetail';

// Tab order for keyboard navigation
const TABS = ['overview', 'performance', 'backtest', 'trades', 'intelligence'];

export function PatternLibraryPage() {
  const { data: strategiesData, isLoading } = useStrategies();
  const { selectedStrategyId, setSelectedStrategy, filters, setFilter, activeTab, setActiveTab } = usePatternLibraryUI();
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  const strategies = strategiesData?.strategies ?? [];
  const sortedStrategies = useSortedStrategies(strategies);

  // On tablet/mobile, selecting a strategy shows detail view (hides grid)
  const showDetail = selectedStrategyId !== null;
  const showGrid = isDesktop || !showDetail;

  // Handle stage filter changes from the pipeline
  const handleStageClick = (stage: string | null) => {
    setFilter('stage', stage);
  };

  // Scroll selected card into view
  const scrollToSelected = useCallback((strategyId: string) => {
    const element = document.querySelector(`[data-strategy-id="${strategyId}"]`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Suppress when typing in inputs
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      // Check if DocumentModal is open (it adds overflow:hidden to body)
      if (document.body.style.overflow === 'hidden') {
        return;
      }

      // Card navigation (arrow keys only)
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (sortedStrategies.length === 0) return;

        const currentIndex = selectedStrategyId
          ? sortedStrategies.findIndex((s) => s.strategy_id === selectedStrategyId)
          : -1;
        const nextIndex = currentIndex < sortedStrategies.length - 1 ? currentIndex + 1 : 0;
        const nextStrategy = sortedStrategies[nextIndex];
        setSelectedStrategy(nextStrategy.strategy_id);
        scrollToSelected(nextStrategy.strategy_id);
        return;
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (sortedStrategies.length === 0) return;

        const currentIndex = selectedStrategyId
          ? sortedStrategies.findIndex((s) => s.strategy_id === selectedStrategyId)
          : 0;
        const prevIndex = currentIndex > 0 ? currentIndex - 1 : sortedStrategies.length - 1;
        const prevStrategy = sortedStrategies[prevIndex];
        setSelectedStrategy(prevStrategy.strategy_id);
        scrollToSelected(prevStrategy.strategy_id);
        return;
      }

      // Escape to deselect
      if (e.key === 'Escape' && selectedStrategyId) {
        e.preventDefault();
        setSelectedStrategy(null);
        return;
      }

      // Tab navigation (only when detail panel is open)
      if (selectedStrategyId) {
        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          const currentTabIndex = TABS.indexOf(activeTab);
          const prevTabIndex = currentTabIndex > 0 ? currentTabIndex - 1 : TABS.length - 1;
          setActiveTab(TABS[prevTabIndex]);
          return;
        }

        if (e.key === 'ArrowRight') {
          e.preventDefault();
          const currentTabIndex = TABS.indexOf(activeTab);
          const nextTabIndex = currentTabIndex < TABS.length - 1 ? currentTabIndex + 1 : 0;
          setActiveTab(TABS[nextTabIndex]);
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [sortedStrategies, selectedStrategyId, setSelectedStrategy, activeTab, setActiveTab, scrollToSelected]);

  if (isLoading) {
    return (
      <AnimatedPage>
        <div className="flex items-center gap-3 mb-6">
          <BookOpen className="w-6 h-6 text-argus-accent" />
          <h1 className="text-xl font-semibold text-argus-text">Pattern Library</h1>
        </div>
        <Card className="mb-6">
          <Skeleton className="h-10" />
        </Card>
        <div className="space-y-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      </AnimatedPage>
    );
  }

  return (
    <AnimatedPage>
      {/* Page header */}
      <div className="flex items-center gap-3 mb-6">
        <BookOpen className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">Pattern Library</h1>
      </div>

      {/* Pipeline visualization */}
      <div className="mb-6">
        <IncubatorPipeline
          strategies={strategies}
          activeStageFilter={filters.stage}
          onStageClick={handleStageClick}
        />
      </div>

      {/* Master-detail layout */}
      <div className={isDesktop ? 'flex gap-6' : ''}>
        {/* Left panel: Card grid */}
        {showGrid && (
          <div className={isDesktop ? 'w-[35%] flex-shrink-0' : 'w-full'}>
            <PatternCardGrid
              strategies={strategies}
              selectedId={selectedStrategyId}
              onSelect={setSelectedStrategy}
            />
          </div>
        )}

        {/* Right panel: Detail view */}
        {showDetail && (
          <div className={isDesktop ? 'flex-1 min-w-0' : 'w-full'}>
            <PatternDetail
              strategyId={selectedStrategyId!}
              onClose={() => setSelectedStrategy(null)}
            />
          </div>
        )}
      </div>
    </AnimatedPage>
  );
}
