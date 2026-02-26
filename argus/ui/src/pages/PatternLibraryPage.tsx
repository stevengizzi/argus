/**
 * Pattern Library page - strategy documentation and analysis hub.
 *
 * Master-detail layout:
 * - Desktop (>=1024px): Left panel 35%, right panel 65%, side by side
 * - Tablet/Mobile (<1024px): Full-width card list, selecting shows detail view
 */

import { BookOpen, ArrowLeft } from 'lucide-react';
import { AnimatedPage } from '../components/AnimatedPage';
import { Card } from '../components/Card';
import { Skeleton } from '../components/Skeleton';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { useStrategies } from '../hooks/useStrategies';
import { usePatternLibraryUI } from '../stores/patternLibraryUI';
import { IncubatorPipeline } from '../features/patterns/IncubatorPipeline';
import { PatternCardGrid } from '../features/patterns/PatternCardGrid';

export function PatternLibraryPage() {
  const { data: strategiesData, isLoading } = useStrategies();
  const { selectedStrategyId, setSelectedStrategy, filters, setFilter } = usePatternLibraryUI();
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  const strategies = strategiesData?.strategies ?? [];

  // On tablet/mobile, selecting a strategy shows detail view (hides grid)
  const showDetail = selectedStrategyId !== null;
  const showGrid = isDesktop || !showDetail;

  // Handle stage filter changes from the pipeline
  const handleStageClick = (stage: string | null) => {
    setFilter('stage', stage);
  };

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

        {/* Right panel: Detail view (placeholder for Sessions 4-6) */}
        {showDetail && (
          <div className={isDesktop ? 'flex-1 min-w-0' : 'w-full'}>
            <PatternDetailPlaceholder
              strategyId={selectedStrategyId!}
              strategies={strategies}
              onClose={() => setSelectedStrategy(null)}
              showBackButton={!isDesktop}
            />
          </div>
        )}
      </div>
    </AnimatedPage>
  );
}

/**
 * Placeholder for PatternDetail component (built in Sessions 4-6).
 */
interface PatternDetailPlaceholderProps {
  strategyId: string;
  strategies: Array<{ strategy_id: string; name: string }>;
  onClose: () => void;
  showBackButton: boolean;
}

function PatternDetailPlaceholder({
  strategyId,
  strategies,
  onClose,
  showBackButton,
}: PatternDetailPlaceholderProps) {
  const strategy = strategies.find((s) => s.strategy_id === strategyId);

  return (
    <Card>
      {showBackButton && (
        <button
          onClick={onClose}
          className="flex items-center gap-2 text-argus-text-dim hover:text-argus-text mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Back to list</span>
        </button>
      )}
      <h2 className="text-lg font-medium text-argus-text mb-2">
        {strategy?.name || strategyId}
      </h2>
      <p className="text-argus-text-dim text-sm">
        Pattern detail view coming in Sessions 4-6.
      </p>
    </Card>
  );
}
