/**
 * Pattern Library detail panel container.
 *
 * Holds the tabbed detail view with:
 * - Strategy header with name and pipeline stage badge
 * - 5 tabs: Overview, Performance, Backtest, Trades, Intelligence
 * - Responsive back button for tablet/mobile
 *
 * Uses SegmentedTab for tab navigation and Zustand store for state persistence.
 */

import { ChevronLeft } from 'lucide-react';
import { Card } from '../../components/Card';
import { Badge } from '../../components/Badge';
import { SegmentedTab } from '../../components/SegmentedTab';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { useStrategies } from '../../hooks/useStrategies';
import { usePatternLibraryUI } from '../../stores/patternLibraryUI';
import { OverviewTab, BacktestTab, PerformanceTab, TradesTab, IntelligenceTab } from './tabs';

interface PatternDetailProps {
  strategyId: string;
  onClose: () => void;
}

// Display labels for pipeline stages
const STAGE_LABELS: Record<string, string> = {
  concept: 'Concept',
  exploration: 'Explore',
  validation: 'Validate',
  ecosystem_replay: 'Eco Replay',
  paper_trading: 'Paper',
  live_minimum: 'Live Min',
  live_full: 'Live Full',
  active_monitoring: 'Monitor',
  suspended: 'Suspended',
  retired: 'Retired',
};

type BadgeVariant = 'info' | 'success' | 'warning' | 'danger' | 'neutral';

/**
 * Returns the Badge variant for a pipeline stage.
 */
function getPipelineBadgeVariant(stage: string): BadgeVariant {
  switch (stage) {
    case 'paper_trading':
      return 'warning';
    case 'live_minimum':
    case 'live_full':
    case 'active_monitoring':
      return 'success';
    case 'concept':
    case 'exploration':
    case 'validation':
    case 'ecosystem_replay':
      return 'info';
    case 'suspended':
      return 'danger';
    case 'retired':
    default:
      return 'neutral';
  }
}

// Tab configuration
const TABS = [
  { value: 'overview', label: 'Overview' },
  { value: 'performance', label: 'Performance' },
  { value: 'backtest', label: 'Backtest' },
  { value: 'trades', label: 'Trades' },
  { value: 'intelligence', label: 'Intelligence' },
];

export function PatternDetail({ strategyId, onClose }: PatternDetailProps) {
  const { activeTab, setActiveTab } = usePatternLibraryUI();
  const { data: strategiesData } = useStrategies();
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  const strategy = strategiesData?.strategies.find((s) => s.strategy_id === strategyId);

  if (!strategy) {
    return (
      <Card>
        <p className="text-argus-text-dim text-sm">Strategy not found.</p>
      </Card>
    );
  }

  const stageLabel = STAGE_LABELS[strategy.pipeline_stage] || strategy.pipeline_stage;
  const badgeVariant = getPipelineBadgeVariant(strategy.pipeline_stage);

  return (
    <div>
      {/* Back button for tablet/mobile */}
      {!isDesktop && (
        <button
          onClick={onClose}
          className="flex items-center gap-1 text-sm text-argus-text-dim hover:text-argus-text mb-4"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to strategies
        </button>
      )}

      {/* Strategy header */}
      <div className="flex items-center gap-3 mb-2">
        <h2 className="text-lg font-semibold text-argus-text">{strategy.name}</h2>
        <Badge variant={badgeVariant}>{stageLabel}</Badge>
      </div>
      {strategy.description_short && (
        <p className="text-sm text-argus-text-dim mb-4">{strategy.description_short}</p>
      )}

      {/* Tab navigation */}
      <div className="mb-4">
        <SegmentedTab
          segments={TABS}
          activeValue={activeTab}
          onChange={setActiveTab}
          size="sm"
          layoutId="pattern-detail-tabs"
        />
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'overview' && <OverviewTab strategy={strategy} />}
        {activeTab === 'performance' && <PerformanceTab strategyId={strategyId} />}
        {activeTab === 'backtest' && <BacktestTab strategy={strategy} />}
        {activeTab === 'trades' && <TradesTab strategyId={strategyId} />}
        {activeTab === 'intelligence' && <IntelligenceTab />}
      </div>
    </div>
  );
}
