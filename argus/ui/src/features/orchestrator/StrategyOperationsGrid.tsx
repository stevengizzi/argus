/**
 * Strategy Operations Grid — responsive grid of per-strategy operation cards.
 *
 * Layout:
 * - Desktop (>=1024px): 2 columns
 * - Mobile (<1024px): 1 column
 *
 * Fetches allocation data from useOrchestratorStatus and renders
 * a StrategyOperationsCard for each strategy.
 */

import { useOrchestratorStatus } from '../../hooks';
import { StrategyOperationsCard } from './StrategyOperationsCard';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { Skeleton } from '../../components/Skeleton';

interface StrategyOperationsGridProps {
  onViewDecisions?: (strategyId: string) => void;
}

export function StrategyOperationsGrid({ onViewDecisions }: StrategyOperationsGridProps) {
  const { data: orchestratorData, isLoading, error } = useOrchestratorStatus();

  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Strategy Operations" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      </Card>
    );
  }

  if (error || !orchestratorData) {
    return (
      <Card>
        <CardHeader title="Strategy Operations" />
        <div className="flex items-center justify-center h-32 text-sm text-argus-text-dim">
          Unable to load strategy data
        </div>
      </Card>
    );
  }

  const allocations = orchestratorData.allocations;

  if (allocations.length === 0) {
    return (
      <Card>
        <CardHeader title="Strategy Operations" />
        <div className="flex items-center justify-center h-32 text-sm text-argus-text-dim">
          No strategies registered
        </div>
      </Card>
    );
  }

  return (
    <div>
      <h3 className="text-sm font-medium text-argus-text-dim mb-3">Strategy Operations</h3>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {allocations.map((allocation) => (
          <StrategyOperationsCard
            key={allocation.strategy_id}
            allocation={allocation}
            onViewDecisions={onViewDecisions}
          />
        ))}
      </div>
    </div>
  );
}
