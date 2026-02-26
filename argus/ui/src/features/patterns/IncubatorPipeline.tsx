/**
 * Incubator Pipeline visualization showing strategy progress through 10 stages.
 *
 * Desktop/Tablet (>=640px): Horizontal flex row with chevron connectors.
 * Mobile (<640px): Horizontal scrollable pills.
 */

import { ChevronRight } from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import type { StrategyInfo } from '../../api/types';

export const PIPELINE_STAGES = [
  { key: 'concept', label: 'Concept' },
  { key: 'exploration', label: 'Explore' },
  { key: 'validation', label: 'Validate' },
  { key: 'ecosystem_replay', label: 'Eco Replay' },
  { key: 'paper_trading', label: 'Paper' },
  { key: 'live_minimum', label: 'Live Min' },
  { key: 'live_full', label: 'Live Full' },
  { key: 'active_monitoring', label: 'Monitor' },
  { key: 'suspended', label: 'Suspended' },
  { key: 'retired', label: 'Retired' },
] as const;

export type PipelineStageKey = (typeof PIPELINE_STAGES)[number]['key'];

interface IncubatorPipelineProps {
  strategies: StrategyInfo[];
  activeStageFilter: string | null;
  onStageClick: (stage: string | null) => void;
}

export function IncubatorPipeline({
  strategies,
  activeStageFilter,
  onStageClick,
}: IncubatorPipelineProps) {
  const isWideScreen = useMediaQuery('(min-width: 640px)');

  // Count strategies per stage
  const stageCounts = PIPELINE_STAGES.map((stage) => ({
    ...stage,
    count: strategies.filter((s) => s.pipeline_stage === stage.key).length,
  }));

  const handleStageClick = (key: string) => {
    // Toggle: clicking the active stage clears the filter
    onStageClick(activeStageFilter === key ? null : key);
  };

  return (
    <Card>
      <CardHeader title="Strategy Pipeline" />
      {isWideScreen ? (
        <DesktopPipeline
          stages={stageCounts}
          activeStage={activeStageFilter}
          onClick={handleStageClick}
        />
      ) : (
        <MobilePipeline
          stages={stageCounts}
          activeStage={activeStageFilter}
          onClick={handleStageClick}
        />
      )}
    </Card>
  );
}

interface StageWithCount {
  key: string;
  label: string;
  count: number;
}

interface PipelineViewProps {
  stages: StageWithCount[];
  activeStage: string | null;
  onClick: (key: string) => void;
}

function DesktopPipeline({ stages, activeStage, onClick }: PipelineViewProps) {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {stages.map((stage, index) => {
        const isActive = activeStage === stage.key;
        return (
          <div key={stage.key} className="flex items-center">
            <button
              onClick={() => onClick(stage.key)}
              className={`
                px-3 py-1.5 rounded-full text-xs font-medium transition-colors
                ${isActive
                  ? 'bg-argus-accent text-white'
                  : stage.count > 0
                    ? 'text-argus-text bg-argus-surface-2 hover:bg-argus-surface-3'
                    : 'text-argus-text-dim bg-transparent hover:bg-argus-surface-3'
                }
              `}
            >
              {stage.label}
              {stage.count > 0 && (
                <span className={isActive ? 'ml-1.5 text-white/70' : 'ml-1.5 text-argus-text-dim'}>
                  ({stage.count})
                </span>
              )}
            </button>
            {index < stages.length - 1 && (
              <ChevronRight className="w-4 h-4 text-argus-text-dim mx-0.5 flex-shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
}

function MobilePipeline({ stages, activeStage, onClick }: PipelineViewProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
      {stages.map((stage) => {
        const isActive = activeStage === stage.key;
        return (
          <button
            key={stage.key}
            onClick={() => onClick(stage.key)}
            className={`
              flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors whitespace-nowrap
              ${isActive
                ? 'bg-argus-accent text-white'
                : stage.count > 0
                  ? 'text-argus-text bg-argus-surface-2'
                  : 'text-argus-text-dim bg-transparent'
              }
            `}
          >
            {stage.label}{' '}
            <span className={isActive ? 'text-white/70' : ''}>({stage.count})</span>
          </button>
        );
      })}
    </div>
  );
}
