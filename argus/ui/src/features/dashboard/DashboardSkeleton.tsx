/**
 * Dashboard page skeleton with content-shaped placeholders.
 *
 * Matches the actual Dashboard layout with precise line heights:
 * - text-3xl: 36px line height
 * - text-xl: 28px line height
 * - text-sm: 20px line height
 * - text-xs: 16px line height
 */

import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { Skeleton } from '../../components/Skeleton';

/** Skeleton for AccountSummary card */
export function AccountSummarySkeleton() {
  return (
    <Card className="h-full">
      {/* Use actual CardHeader for correct spacing (mb-3) */}
      <CardHeader title="Account Equity" />

      {/* Hero equity number - text-3xl has 36px line height */}
      <Skeleton variant="line" width="60%" height={36} />

      {/* Supporting metrics grid - mt-3 matches actual */}
      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          {/* Label - text-argus-text-dim is text size inherit (14px/20px) */}
          <Skeleton variant="line" width={40} height={20} className="mb-0" />
          {/* Value - text-sm is 14px/20px */}
          <Skeleton variant="line" width={80} height={20} />
        </div>
        <div>
          <Skeleton variant="line" width={80} height={20} className="mb-0" />
          <Skeleton variant="line" width={80} height={20} />
        </div>
      </div>
    </Card>
  );
}

/** Skeleton for DailyPnlCard */
export function DailyPnlSkeleton() {
  return (
    <Card className="h-full">
      <CardHeader title="Daily P&L" />

      {/* Hero P&L number - PnlValue xl uses text-3xl (36px line height) */}
      <div className="flex items-baseline gap-2">
        <Skeleton variant="line" width="50%" height={36} />
      </div>

      {/* Percentage - mt-1, PnlValue sm uses text-sm (20px line height) */}
      <div className="mt-1">
        <Skeleton variant="line" width={60} height={20} />
      </div>

      {/* Trade count - mt-3 text-sm (20px line height) */}
      <div className="mt-3">
        <Skeleton variant="line" width={100} height={20} />
      </div>
    </Card>
  );
}

/** Skeleton for MarketStatusBadge */
export function MarketStatusSkeleton() {
  return (
    <Card className="h-full">
      <CardHeader title="Market" />

      {/* Status with dot - flex items-center gap-2 */}
      <div className="flex items-center gap-2">
        {/* StatusDot is 12px (w-3 h-3 for md) */}
        <Skeleton variant="circle" width={12} height={12} />
        {/* Status text is text-xl (28px line height) */}
        <Skeleton variant="line" width={80} height={28} />
      </div>

      {/* Time - mt-2 text-sm (20px line height) */}
      <div className="mt-2">
        <Skeleton variant="line" width={100} height={20} />
      </div>

      {/* Paper badge - mt-3, Badge is ~22px tall */}
      <div className="mt-3">
        <Skeleton variant="rect" width={60} height={22} rounded />
      </div>
    </Card>
  );
}

/** Skeleton for OpenPositions table */
export function OpenPositionsSkeleton() {
  return (
    <Card noPadding>
      {/* CardHeader with subtitle - p-4 pb-0 */}
      <div className="p-4 pb-0">
        <CardHeader
          title="Open Positions"
          subtitle="0 positions"
        />
      </div>

      {/* Table header - hidden lg:block, bg-argus-surface-2 */}
      <div className="hidden lg:block px-4 py-2 bg-argus-surface-2">
        <div className="flex gap-4">
          {/* Column headers are text-xs uppercase (16px line height) */}
          {Array.from({ length: 7 }).map((_, i) => (
            <Skeleton key={i} variant="line" width={60} height={16} />
          ))}
        </div>
      </div>

      {/* Table rows */}
      <div className="divide-y divide-argus-border">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Symbol - text-sm font-semibold (20px) */}
              <Skeleton variant="line" width={50} height={20} />
              {/* Side badge */}
              <Skeleton variant="rect" width={40} height={20} rounded />
            </div>
            <div className="flex items-center gap-4">
              {/* P&L - text-sm (20px) */}
              <Skeleton variant="line" width={70} height={20} />
              {/* R value */}
              <Skeleton variant="line" width={40} height={20} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/** Skeleton for RecentTrades */
export function RecentTradesSkeleton() {
  return (
    <Card noPadding>
      <div className="p-4 pb-0">
        <CardHeader
          title="Recent Trades"
          subtitle="Last 8"
        />
      </div>

      {/* Trade list - divide-y */}
      <div className="divide-y divide-argus-border">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="px-4 py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Symbol - text-sm font-medium (20px) */}
              <Skeleton variant="line" width={48} height={20} />
              {/* P&L - text-sm (20px) */}
              <Skeleton variant="line" width={60} height={20} />
            </div>
            <div className="flex items-center gap-3">
              {/* Exit reason badge - ~20px */}
              <Skeleton variant="rect" width={30} height={20} rounded />
              {/* Time - text-xs (16px) */}
              <Skeleton variant="line" width={50} height={16} />
            </div>
          </div>
        ))}
      </div>

      {/* Footer link - border-t, p-4 pt-3 */}
      <div className="p-4 pt-3 border-t border-argus-border">
        {/* Link text is text-sm (20px) */}
        <Skeleton variant="line" width={110} height={20} />
      </div>
    </Card>
  );
}

/** Skeleton for HealthMini */
export function HealthMiniSkeleton() {
  return (
    <Card>
      {/* CardHeader with action */}
      <div className="flex items-center justify-between mb-3">
        {/* Title - text-sm uppercase (20px line height) */}
        <Skeleton variant="line" width={100} height={20} />
        <div className="flex items-center gap-1.5">
          {/* StatusDot sm is 8px */}
          <Skeleton variant="circle" width={8} height={8} />
          {/* Status text - text-xs uppercase (16px) */}
          <Skeleton variant="line" width={40} height={16} />
        </div>
      </div>

      {/* Component list - space-y-2 */}
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              {/* StatusDot sm is 8px */}
              <Skeleton variant="circle" width={8} height={8} />
              {/* Component name - text-sm (20px) */}
              <Skeleton variant="line" width={80} height={20} />
            </div>
            {/* Status text - text-xs (16px) */}
            <Skeleton variant="line" width={50} height={16} />
          </div>
        ))}
      </div>

      {/* Uptime footer - mt-4 pt-3 border-t */}
      <div className="mt-4 pt-3 border-t border-argus-border flex items-center justify-between text-sm">
        {/* Uptime label with icon - text-sm (20px) */}
        <Skeleton variant="line" width={70} height={20} />
        {/* Uptime value - text-sm tabular-nums (20px) */}
        <Skeleton variant="line" width={60} height={20} />
      </div>
    </Card>
  );
}
