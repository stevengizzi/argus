/**
 * Trades page skeleton with content-shaped placeholders.
 *
 * Matches actual Trades page layout with precise line heights:
 * - text-lg: 28px line height
 * - text-sm: 20px line height
 * - text-xs: 16px line height
 */

import { Skeleton } from '../../components/Skeleton';

/** Skeleton for TradeFilters */
export function TradeFiltersSkeleton() {
  return (
    <div className="bg-argus-surface border border-argus-border rounded-lg p-3 md:p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
        {/* Strategy dropdown */}
        <div className="flex-1 min-w-0">
          {/* Label: text-xs uppercase = 16px line height */}
          <Skeleton variant="line" width={60} height={16} className="mb-1" />
          {/* Select: px-3 py-2 text-sm = ~38px */}
          <Skeleton variant="rect" height={38} />
        </div>

        {/* Outcome toggle */}
        <div className="w-full md:w-auto md:flex-shrink-0">
          <Skeleton variant="line" width={55} height={16} className="mb-1" />
          <div className="flex rounded-md border border-argus-border overflow-hidden">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton
                key={i}
                variant="rect"
                width={50}
                height={44}
                rounded={false}
              />
            ))}
          </div>
        </div>

        {/* Date range */}
        <div className="flex gap-3 w-full md:flex-1">
          <div className="flex-1 min-w-0">
            <Skeleton variant="line" width={35} height={16} className="mb-1" />
            <Skeleton variant="rect" height={38} />
          </div>
          <div className="flex-1 min-w-0">
            <Skeleton variant="line" width={20} height={16} className="mb-1" />
            <Skeleton variant="rect" height={38} />
          </div>
        </div>
      </div>
    </div>
  );
}

/** Skeleton for TradeStatsBar - uses MetricCard component */
export function TradeStatsBarSkeleton() {
  return (
    <div className="bg-argus-surface border border-argus-border rounded-lg p-3 md:p-4">
      <div className="flex items-center justify-around gap-4">
        {/* Trades metric - MetricCard structure */}
        <div className="text-center">
          {/* Label: text-xs uppercase = 16px, mb-1 */}
          <Skeleton variant="line" width={45} height={16} className="mb-1 mx-auto" />
          {/* Value: text-lg = 28px line height */}
          <Skeleton variant="line" width={30} height={28} className="mx-auto" />
          {/* SubValue: text-xs mt-0.5 = 16px */}
          <Skeleton variant="line" width={55} height={16} className="mt-0.5 mx-auto" />
        </div>

        <div className="w-px h-8 bg-argus-border" />

        {/* Win Rate metric */}
        <div className="text-center">
          <Skeleton variant="line" width={55} height={16} className="mb-1 mx-auto" />
          {/* Value with trend icon - flex gap-1 */}
          <div className="flex items-center justify-center gap-1">
            <Skeleton variant="line" width={45} height={28} />
            <Skeleton variant="circle" width={12} height={12} />
          </div>
        </div>

        <div className="w-px h-8 bg-argus-border hidden sm:block" />

        {/* Net P&L metric */}
        <div className="hidden sm:block text-center">
          <Skeleton variant="line" width={45} height={16} className="mb-1 mx-auto" />
          <div className="flex items-center justify-center gap-1">
            <Skeleton variant="line" width={65} height={28} />
            <Skeleton variant="circle" width={12} height={12} />
          </div>
        </div>
      </div>
    </div>
  );
}

/** Skeleton for TradeTable */
export function TradeTableSkeleton() {
  return (
    <div className="bg-argus-surface border border-argus-border rounded-lg overflow-hidden">
      {/* Table header - text-xs uppercase = 16px */}
      <div className="bg-argus-surface-2 px-3 py-2">
        <div className="flex items-center gap-4">
          <Skeleton variant="line" width={50} height={16} />
          <Skeleton variant="line" width={50} height={16} className="hidden md:block" />
          <Skeleton variant="line" width={40} height={16} className="hidden md:block" />
          <Skeleton variant="line" width={30} height={16} />
          <Skeleton variant="line" width={30} height={16} className="hidden md:block" />
          <Skeleton variant="line" width={30} height={16} />
          <Skeleton variant="line" width={50} height={16} className="hidden lg:block" />
        </div>
      </div>

      {/* Table rows - py-2.5 text-sm = 20px line height */}
      <div className="divide-y divide-argus-border">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="px-3 py-2.5">
            <div className="flex items-center gap-4">
              {/* Trade info (phone: combined, desktop: separate) */}
              <div className="lg:hidden flex-1">
                {/* Symbol: font-medium text-sm = 20px */}
                <Skeleton variant="line" width={60} height={20} className="mb-0.5" />
                {/* Date: text-xs = 16px */}
                <Skeleton variant="line" width={80} height={16} />
              </div>
              {/* Desktop separate columns - text-sm = 20px */}
              <Skeleton variant="line" width={80} height={20} className="hidden lg:block" />
              <Skeleton variant="line" width={50} height={20} className="hidden lg:block" />
              <Skeleton variant="line" width={40} height={20} className="hidden lg:block" />

              {/* Entry/Exit prices - text-sm = 20px */}
              <Skeleton variant="line" width={60} height={20} className="hidden md:block" />
              <Skeleton variant="line" width={60} height={20} className="hidden md:block" />

              {/* P&L */}
              <Skeleton variant="line" width={70} height={20} />

              {/* R-multiple */}
              <Skeleton variant="line" width={40} height={20} className="hidden md:block" />

              {/* Exit reason badge - Badge is ~20px */}
              <Skeleton variant="rect" width={35} height={20} rounded />

              {/* Duration */}
              <Skeleton variant="line" width={50} height={20} className="hidden lg:block" />
            </div>
          </div>
        ))}
      </div>

      {/* Pagination - py-3 */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-argus-border bg-argus-surface-2">
        {/* Prev button - min-h-[44px] */}
        <Skeleton variant="rect" width={70} height={44} rounded />
        {/* Page indicator - text-sm = 20px */}
        <Skeleton variant="line" width={90} height={20} />
        {/* Next button */}
        <Skeleton variant="rect" width={70} height={44} rounded />
      </div>
    </div>
  );
}

/** Full Trades page skeleton */
export function TradesSkeleton() {
  return (
    <div className="space-y-4 md:space-y-6">
      <TradeFiltersSkeleton />
      <TradeStatsBarSkeleton />
      <TradeTableSkeleton />
    </div>
  );
}
