/**
 * System page skeleton with content-shaped placeholders.
 *
 * Matches actual System page layout with precise line heights:
 * - text-lg: 28px line height
 * - text-sm: 20px line height
 * - text-xs: 16px line height
 */

import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { Skeleton } from '../../components/Skeleton';

/** Skeleton for SystemOverview */
export function SystemOverviewSkeleton() {
  return (
    <Card>
      {/* Status header - flex items-center justify-between mb-4 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {/* StatusDot md = 12px */}
          <Skeleton variant="circle" width={12} height={12} />
          {/* text-lg font-semibold = 28px */}
          <Skeleton variant="line" width={130} height={28} />
        </div>
        {/* Badge ~22px */}
        <Skeleton variant="rect" width={60} height={22} rounded />
      </div>

      {/* Metadata rows - space-y-2 */}
      <div className="space-y-2">
        {/* MetaRow: text-sm = 20px */}
        <div className="flex items-center justify-between text-sm">
          <Skeleton variant="line" width={50} height={20} />
          <Skeleton variant="line" width={70} height={20} />
        </div>
        <div className="flex items-center justify-between text-sm">
          <Skeleton variant="line" width={40} height={20} />
          <Skeleton variant="line" width={100} height={20} />
        </div>

        <div className="border-t border-argus-border my-3" />

        {/* Sources section header: text-xs uppercase = 16px */}
        <Skeleton variant="line" width={55} height={16} className="mb-2" />
        <div className="flex items-center justify-between text-sm">
          <Skeleton variant="line" width={50} height={20} />
          <Skeleton variant="line" width={110} height={20} />
        </div>
        <div className="flex items-center justify-between text-sm">
          <Skeleton variant="line" width={40} height={20} />
          <Skeleton variant="line" width={75} height={20} />
        </div>

        <div className="border-t border-argus-border my-3" />

        {/* Timestamps section header */}
        <Skeleton variant="line" width={95} height={16} className="mb-2" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center justify-between text-sm">
            <Skeleton variant="line" width={90} height={20} />
            <Skeleton variant="line" width={65} height={20} />
          </div>
        ))}
      </div>
    </Card>
  );
}

/** Skeleton for ComponentStatusList */
export function ComponentStatusListSkeleton() {
  return (
    <Card>
      {/* Use actual CardHeader for correct spacing */}
      <CardHeader
        title="Components"
        subtitle="0 registered"
      />

      {/* Component list - space-y-2 */}
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="flex items-start justify-between py-2 border-b border-argus-border last:border-b-0"
          >
            <div className="flex items-start gap-2.5">
              {/* StatusDot sm = 8px */}
              <Skeleton variant="circle" width={8} height={8} className="mt-1.5" />
              <div className="flex-1">
                {/* Name: text-sm font-medium = 20px */}
                <Skeleton variant="line" width={100} height={20} className="mb-0.5" />
                {/* Details: text-xs = 16px */}
                <Skeleton variant="line" width={150} height={16} />
              </div>
            </div>
            {/* Status text: text-xs uppercase = 16px */}
            <Skeleton variant="line" width={55} height={16} />
          </div>
        ))}
      </div>
    </Card>
  );
}

/** Skeleton for StrategyCards */
export function StrategyCardsSkeleton() {
  return (
    <div>
      {/* Header using CardHeader for correct spacing */}
      <CardHeader
        title="Strategies"
        subtitle="0 configured"
      />

      {/* Strategy cards - space-y-4 */}
      <div className="space-y-4">
        {Array.from({ length: 2 }).map((_, i) => (
          <Card key={i}>
            {/* Header with name and badges - flex items-start justify-between mb-4 */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-start gap-2.5">
                {/* StatusDot sm = 8px, needs margin-top to align with text */}
                <Skeleton variant="circle" width={8} height={8} className="mt-1.5" />
                <div>
                  {/* Name: text-sm font-semibold = 20px */}
                  <Skeleton variant="line" width={100} height={20} className="mb-1" />
                  {/* Version: text-xs = 16px */}
                  <Skeleton variant="line" width={30} height={16} />
                </div>
              </div>
              {/* Badge ~20px */}
              <Skeleton variant="rect" width={55} height={20} rounded />
            </div>

            {/* Stats grid - grid-cols-2 gap-x-4 gap-y-2 mb-4 */}
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 mb-4">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className="text-sm">
                  {/* Label: text-argus-text-dim = text-sm = 20px */}
                  <Skeleton variant="line" width={50} height={20} className="mb-0" />
                  {/* Value: tabular-nums = text-sm = 20px */}
                  <Skeleton variant="line" width={60} height={20} />
                </div>
              ))}
            </div>

            {/* Config summary - pt-3 border-t */}
            <div className="pt-3 border-t border-argus-border">
              {/* text-xs font-mono = 16px */}
              <Skeleton variant="line" width="80%" height={16} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

/** Skeleton for EventsLog (collapsed state) */
export function EventsLogSkeleton() {
  return (
    <Card noPadding>
      {/* Header button - p-4 flex items-center justify-between */}
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-2">
          {/* Chevron icon - w-4 h-4 = 16px */}
          <Skeleton variant="rect" width={16} height={16} />
          {/* text-sm font-medium uppercase = 20px */}
          <Skeleton variant="line" width={100} height={20} />
          {/* Count: text-xs = 16px */}
          <Skeleton variant="line" width={25} height={16} />
          {/* Connection dot - w-1.5 h-1.5 = 6px */}
          <Skeleton variant="circle" width={6} height={6} />
        </div>
      </div>
    </Card>
  );
}

/** Full System page skeleton */
export function SystemSkeleton() {
  return (
    <div className="space-y-6">
      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left column */}
        <div className="space-y-6">
          <SystemOverviewSkeleton />
          <ComponentStatusListSkeleton />
        </div>

        {/* Right column */}
        <StrategyCardsSkeleton />
      </div>

      {/* Events log */}
      <EventsLogSkeleton />
    </div>
  );
}
