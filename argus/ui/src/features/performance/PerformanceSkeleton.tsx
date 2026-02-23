/**
 * Performance page skeleton with content-shaped placeholders.
 *
 * Matches actual Performance page layout with precise line heights:
 * - text-lg: 28px line height (MetricCard values)
 * - text-sm: 20px line height (table cells)
 * - text-xs: 16px line height (labels, headers)
 *
 * Chart heights: 180px mobile, 220px tablet, 300px desktop
 */

import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { Skeleton } from '../../components/Skeleton';

/** Skeleton for PeriodSelector */
export function PeriodSelectorSkeleton() {
  return (
    <div className="flex gap-1">
      {/* 4 period buttons with min-h-[44px] */}
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} variant="rect" width={60} height={44} rounded />
      ))}
    </div>
  );
}

/** Skeleton for MetricsGrid - uses MetricCard component */
export function MetricsGridSkeleton() {
  return (
    <Card>
      {/* Primary metrics row - 6 MetricCard items */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="text-center">
            {/* Label: text-xs uppercase = 16px, mb-1 */}
            <Skeleton variant="line" width={50} height={16} className="mb-1 mx-auto" />
            {/* Value: text-lg = 28px */}
            <Skeleton variant="line" width={60} height={28} className="mx-auto" />
          </div>
        ))}
      </div>

      {/* Secondary metrics row (tablet+) - mt-4 pt-4 border-t */}
      <div className="hidden md:grid grid-cols-4 lg:grid-cols-6 gap-4 mt-4 pt-4 border-t border-argus-border">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="text-center">
            <Skeleton variant="line" width={55} height={16} className="mb-1 mx-auto" />
            <Skeleton variant="line" width={50} height={28} className="mx-auto" />
          </div>
        ))}
      </div>
    </Card>
  );
}

/** Skeleton for EquityCurve chart */
export function EquityCurveSkeleton() {
  return (
    <Card noPadding>
      <div className="p-4 pb-0">
        <CardHeader title="Equity Curve" />
      </div>
      {/* Chart: responsive heights (using 300px default, CSS handles responsive) */}
      <div className="h-[180px] sm:h-[220px] lg:h-[300px]">
        <Skeleton variant="rect" height="100%" className="rounded-none" />
      </div>
    </Card>
  );
}

/** Skeleton for DailyPnlChart */
export function DailyPnlChartSkeleton() {
  return (
    <Card noPadding>
      <div className="p-4 pb-0">
        <CardHeader title="Daily P&L" />
      </div>
      {/* Chart: responsive heights */}
      <div className="h-[180px] sm:h-[200px] lg:h-[250px]">
        <Skeleton variant="rect" height="100%" className="rounded-none" />
      </div>
    </Card>
  );
}

/** Skeleton for StrategyBreakdown table */
export function StrategyBreakdownSkeleton() {
  return (
    <Card noPadding>
      <div className="p-4 pb-0">
        <CardHeader title="By Strategy" />
      </div>

      {/* DataTable structure */}
      <div className="overflow-x-auto">
        {/* Table header - text-xs uppercase = 16px */}
        <div className="bg-argus-surface-2 px-3 py-2">
          <div className="flex items-center gap-4">
            <Skeleton variant="line" width={60} height={16} />
            <Skeleton variant="line" width={45} height={16} />
            <Skeleton variant="line" width={55} height={16} />
            <Skeleton variant="line" width={25} height={16} className="hidden md:block" />
            <Skeleton variant="line" width={55} height={16} />
          </div>
        </div>

        {/* Table rows - py-2.5 text-sm = 20px */}
        <div className="divide-y divide-argus-border">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="px-3 py-2.5">
              <div className="flex items-center gap-4">
                {/* Strategy name - font-medium */}
                <Skeleton variant="line" width={100} height={20} />
                {/* Trades */}
                <Skeleton variant="line" width={30} height={20} />
                {/* Win Rate */}
                <Skeleton variant="line" width={45} height={20} />
                {/* PF (hidden on mobile) */}
                <Skeleton variant="line" width={35} height={20} className="hidden md:block" />
                {/* Net P&L */}
                <Skeleton variant="line" width={70} height={20} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

/** Full Performance page skeleton */
export function PerformanceSkeleton() {
  return (
    <div className="space-y-4 md:space-y-6">
      <MetricsGridSkeleton />
      <EquityCurveSkeleton />
      <DailyPnlChartSkeleton />
      <StrategyBreakdownSkeleton />
    </div>
  );
}
