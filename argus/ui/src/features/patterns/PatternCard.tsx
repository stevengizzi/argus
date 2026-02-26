/**
 * Individual strategy card for the Pattern Library grid.
 *
 * Displays strategy name, pipeline stage, family badge, time window,
 * and mini performance stats.
 */

import { Card } from '../../components/Card';
import { Badge } from '../../components/Badge';
import type { StrategyInfo } from '../../api/types';
import type { PipelineStageKey } from './IncubatorPipeline';

interface PatternCardProps {
  strategy: StrategyInfo;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

// Display labels for strategy families
const FAMILY_LABELS: Record<string, string> = {
  orb_family: 'ORB Family',
  momentum: 'Momentum',
  mean_reversion: 'Mean-Reversion',
};

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
  switch (stage as PipelineStageKey) {
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

export function PatternCard({ strategy, isSelected, onSelect }: PatternCardProps) {
  const stageLabel = STAGE_LABELS[strategy.pipeline_stage] || strategy.pipeline_stage;
  const familyLabel = FAMILY_LABELS[strategy.family] || strategy.family;
  const badgeVariant = getPipelineBadgeVariant(strategy.pipeline_stage);

  const perf = strategy.performance_summary;

  return (
    <Card
      interactive
      className={`cursor-pointer ${isSelected ? 'ring-2 ring-argus-accent' : ''}`}
    >
      <div onClick={() => onSelect(strategy.strategy_id)} className="space-y-2">
        {/* Top row: Name + Pipeline stage badge */}
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-argus-text truncate">{strategy.name}</span>
          <Badge variant={badgeVariant}>{stageLabel}</Badge>
        </div>

        {/* Second row: Family + Time window */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-argus-text-dim">{familyLabel}</span>
          <span className="text-argus-border">|</span>
          <span className="text-argus-text-dim">{strategy.time_window}</span>
        </div>

        {/* Bottom row: Mini stats */}
        <div className="flex items-center gap-4 text-xs pt-1">
          <StatItem label="Trades" value={perf ? perf.trade_count : null} />
          <StatItem
            label="Win %"
            value={perf ? `${(perf.win_rate * 100).toFixed(0)}%` : null}
          />
          <StatItem
            label="P&L"
            value={perf ? formatPnl(perf.net_pnl) : null}
            isProfit={perf ? perf.net_pnl >= 0 : undefined}
          />
        </div>
      </div>
    </Card>
  );
}

interface StatItemProps {
  label: string;
  value: string | number | null;
  isProfit?: boolean;
}

function StatItem({ label, value, isProfit }: StatItemProps) {
  const displayValue = value === null ? '—' : value;

  let colorClass = 'text-argus-text';
  if (isProfit !== undefined) {
    colorClass = isProfit ? 'text-argus-profit' : 'text-argus-loss';
  }

  return (
    <div className="flex flex-col">
      <span className="text-argus-text-dim">{label}</span>
      <span className={`font-medium tabular-nums ${colorClass}`}>{displayValue}</span>
    </div>
  );
}

function formatPnl(value: number): string {
  const prefix = value >= 0 ? '+' : '';
  return `${prefix}$${Math.abs(value).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}
