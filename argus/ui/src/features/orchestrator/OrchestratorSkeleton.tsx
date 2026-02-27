/**
 * Skeleton loading state for Orchestrator page.
 *
 * Matches the structure of:
 * - RegimePanel: badge + indicator rows
 * - StrategyCoverageTimeline: bars for each strategy
 * - StrategyOperationsGrid: 4 strategy cards
 * - DecisionTimeline: 5 decision items
 * - GlobalControls: button row
 */

import { Card } from '../../components/Card';
import { Skeleton } from '../../components/Skeleton';

export function OrchestratorSkeleton() {
  return (
    <div className="space-y-6">
      {/* RegimePanel skeleton */}
      <Card>
        <div className="space-y-4">
          {/* Header row: badge + session phase */}
          <div className="flex items-center justify-between">
            <Skeleton variant="rect" width={96} height={24} className="rounded-full" />
            <Skeleton variant="line" width={120} height={16} />
          </div>
          {/* Indicator rows */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Skeleton variant="line" width={64} height={14} />
              <Skeleton variant="line" width={100} height={14} />
              <Skeleton variant="line" width={80} height={14} />
            </div>
            <div className="flex items-center gap-2">
              <Skeleton variant="line" width={64} height={14} />
              <Skeleton variant="line" width={80} height={14} />
            </div>
            <div className="flex items-center gap-2">
              <Skeleton variant="line" width={64} height={14} />
              <Skeleton variant="line" width={100} height={14} />
            </div>
          </div>
        </div>
      </Card>

      {/* StrategyCoverageTimeline skeleton */}
      <Card>
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between">
            <Skeleton variant="line" width={140} height={16} />
            <Skeleton variant="line" width={100} height={12} />
          </div>
          {/* Timeline bars */}
          <div className="h-32 relative">
            {/* Time axis */}
            <div className="flex justify-between mb-2">
              {[...Array(7)].map((_, i) => (
                <Skeleton key={i} variant="line" width={32} height={10} />
              ))}
            </div>
            {/* Strategy bars */}
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Skeleton variant="line" width={60} height={12} />
                  <div className="flex-1">
                    <Skeleton
                      variant="rect"
                      height={20}
                      className="rounded"
                      width={`${40 + i * 15}%`}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* Capital Allocation + Session Overview skeleton (2-column) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Capital Allocation skeleton */}
        <Card>
          <div className="flex items-center gap-6">
            <Skeleton variant="circle" width={100} height={100} />
            <div className="flex-1 space-y-2">
              <Skeleton variant="line" width={120} height={16} />
              <Skeleton variant="line" height={12} />
              <Skeleton variant="line" height={12} />
            </div>
          </div>
        </Card>

        {/* Session Overview skeleton */}
        <Card>
          <div className="space-y-4">
            <Skeleton variant="line" width={120} height={16} />
            {/* P&L prominent */}
            <div className="flex flex-col items-center py-2">
              <Skeleton variant="line" width={80} height={12} />
              <Skeleton variant="line" width={100} height={32} className="mt-1" />
            </div>
            {/* Metric rows */}
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="flex justify-between">
                  <Skeleton variant="line" width={100} height={14} />
                  <Skeleton variant="line" width={50} height={14} />
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* StrategyOperationsGrid skeleton (4 cards) */}
      <div className="grid grid-cols-1 min-[834px]:grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="border-l-4 border-l-gray-600">
            <div className="space-y-3">
              {/* Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Skeleton variant="line" width={100} height={16} />
                  <Skeleton variant="rect" width={48} height={20} className="rounded" />
                </div>
                <Skeleton variant="circle" width={24} height={24} />
              </div>
              {/* Allocation section */}
              <div className="space-y-1">
                <div className="flex justify-between">
                  <Skeleton variant="line" width={60} height={12} />
                  <Skeleton variant="line" width={80} height={12} />
                </div>
                <Skeleton variant="rect" height={6} className="rounded-full" />
              </div>
              {/* Performance row */}
              <div className="flex gap-4">
                <Skeleton variant="line" width={60} height={12} />
                <Skeleton variant="line" width={60} height={12} />
                <Skeleton variant="line" width={50} height={12} />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* DecisionTimeline skeleton */}
      <Card>
        <div className="space-y-3">
          <Skeleton variant="line" width={140} height={16} />
          {/* Decision items */}
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-argus-border last:border-0">
                <Skeleton variant="line" width={50} height={12} />
                <Skeleton variant="rect" width={64} height={20} className="rounded" />
                <Skeleton variant="line" height={12} className="flex-1" />
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* GlobalControls skeleton */}
      <Card>
        <div className="flex flex-wrap gap-3">
          <Skeleton variant="rect" width={120} height={36} className="rounded-md" />
          <Skeleton variant="rect" width={100} height={36} className="rounded-md" />
          <Skeleton variant="rect" width={110} height={36} className="rounded-md" />
        </div>
      </Card>
    </div>
  );
}
