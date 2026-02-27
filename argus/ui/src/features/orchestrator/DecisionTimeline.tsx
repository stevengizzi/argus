/**
 * Decision timeline card.
 *
 * Displays today's orchestrator decisions in chronological order.
 * Scrollable with max height, shows empty state when no decisions.
 */

import { ClipboardList } from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { EmptyState } from '../../components/EmptyState';
import { Skeleton } from '../../components/Skeleton';
import { useOrchestratorDecisions } from '../../hooks';
import { DecisionTimelineItem } from './DecisionTimelineItem';

export function DecisionTimeline() {
  const { data, isLoading, error } = useOrchestratorDecisions();

  if (isLoading) {
    return (
      <div>
        <CardHeader title="Decision Log" />
        <Card>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-start gap-3">
                <Skeleton className="w-16 h-4" />
                <Skeleton className="w-6 h-6 rounded-full" />
                <Skeleton className="flex-1 h-10" />
              </div>
            ))}
          </div>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <CardHeader title="Decision Log" />
        <Card>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <p className="text-argus-warning mb-2 text-sm">
              Unable to load decisions
            </p>
            <p className="text-xs text-argus-text-dim">
              {error.message}
            </p>
          </div>
        </Card>
      </div>
    );
  }

  // Sort decisions reverse chronologically (newest first for operational relevance)
  const decisions = [...(data?.decisions ?? [])].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div>
      <CardHeader
        title="Decision Log"
        subtitle={decisions.length > 0 ? `${decisions.length} today · newest first` : undefined}
      />
      <Card>
        {decisions.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            message="No decisions logged today"
          />
        ) : (
          <div className="max-h-[400px] overflow-y-auto -mx-4 px-4">
            {decisions.map((decision, index) => (
              <DecisionTimelineItem
                key={decision.id}
                decision={decision}
                isFirst={index === 0}
                isLast={index === decisions.length - 1}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
