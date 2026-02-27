/**
 * Skeleton loading states for The Debrief page.
 *
 * Three variants, one per tab:
 * - BriefingSkeleton: Vertical list of briefing card placeholders
 * - ResearchSkeleton: Grid of document card placeholders
 * - JournalSkeleton: Form input + entry card placeholders
 */

import { Card } from '../../components/Card';
import { Skeleton } from '../../components/Skeleton';
import type { DebriefSection } from '../../stores/debriefUI';

interface DebriefSkeletonProps {
  section: DebriefSection;
}

/**
 * Skeleton for briefings tab — vertical list of cards.
 */
function BriefingSkeleton() {
  return (
    <div className="space-y-4">
      {/* Header row with button */}
      <div className="flex items-center justify-between">
        <Skeleton variant="line" width={100} height={20} />
        <Skeleton variant="rect" width={120} height={36} className="rounded-md" />
      </div>

      {/* Briefing cards */}
      {[...Array(4)].map((_, i) => (
        <Card key={i}>
          <div className="space-y-3">
            {/* Header row: date + badges */}
            <div className="flex items-center gap-2">
              <Skeleton variant="line" width={100} height={14} />
              <Skeleton variant="rect" width={72} height={22} className="rounded-full" />
              <Skeleton variant="rect" width={56} height={22} className="rounded-full" />
            </div>
            {/* Title */}
            <Skeleton variant="line" width="70%" height={18} />
            {/* Content preview */}
            <Skeleton variant="line" height={14} />
            <Skeleton variant="line" width="85%" height={14} />
            {/* Footer row */}
            <div className="flex items-center justify-between pt-2">
              <div className="flex items-center gap-4">
                <Skeleton variant="line" width={60} height={12} />
                <Skeleton variant="line" width={80} height={12} />
              </div>
              <div className="flex items-center gap-2">
                <Skeleton variant="circle" width={24} height={24} />
                <Skeleton variant="circle" width={24} height={24} />
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

/**
 * Skeleton for research library tab — grid of document cards.
 */
function ResearchSkeleton() {
  return (
    <div className="space-y-4">
      {/* Header row with button */}
      <div className="flex items-center justify-between">
        <Skeleton variant="line" width={140} height={20} />
        <Skeleton variant="rect" width={120} height={36} className="rounded-md" />
      </div>

      {/* Category filter tabs */}
      <Skeleton variant="rect" height={44} className="rounded-lg max-w-xl" />

      {/* Document grid */}
      <div className="grid grid-cols-1 min-[834px]:grid-cols-2 gap-4">
        {[...Array(6)].map((_, i) => (
          <Card key={i}>
            <div className="space-y-3">
              {/* Header: category + source badges */}
              <div className="flex items-center justify-between">
                <Skeleton variant="rect" width={72} height={22} className="rounded-full" />
                <Skeleton variant="rect" width={56} height={18} className="rounded" />
              </div>
              {/* Title */}
              <Skeleton variant="line" width="80%" height={18} />
              {/* Tags */}
              <div className="flex gap-2">
                <Skeleton variant="rect" width={48} height={20} className="rounded-full" />
                <Skeleton variant="rect" width={56} height={20} className="rounded-full" />
                <Skeleton variant="rect" width={40} height={20} className="rounded-full" />
              </div>
              {/* Footer */}
              <div className="flex items-center gap-4 pt-2">
                <Skeleton variant="line" width={60} height={12} />
                <Skeleton variant="line" width={80} height={12} />
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

/**
 * Skeleton for journal tab — form input + entry list.
 */
function JournalSkeleton() {
  return (
    <div className="space-y-4">
      {/* Collapsed form placeholder */}
      <Card>
        <Skeleton variant="line" height={40} className="rounded-md" />
      </Card>

      {/* Filter row */}
      <div className="flex flex-wrap gap-3">
        <Skeleton variant="rect" width={120} height={36} className="rounded-md" />
        <Skeleton variant="rect" width={140} height={36} className="rounded-md" />
        <Skeleton variant="rect" width={100} height={36} className="rounded-md" />
        <Skeleton variant="rect" width={160} height={36} className="rounded-md flex-1" />
      </div>

      {/* Entry count */}
      <Skeleton variant="line" width={140} height={14} />

      {/* Journal entry cards */}
      {[...Array(5)].map((_, i) => (
        <Card key={i}>
          <div className="space-y-3">
            {/* Header: type badge + title */}
            <div className="flex items-center gap-2">
              <Skeleton variant="rect" width={80} height={22} className="rounded-full" />
              <Skeleton variant="line" width="60%" height={16} />
            </div>
            {/* Content preview */}
            <Skeleton variant="line" height={14} />
            <Skeleton variant="line" width="75%" height={14} />
            {/* Tags row */}
            <div className="flex gap-2">
              <Skeleton variant="rect" width={56} height={20} className="rounded-full" />
              <Skeleton variant="rect" width={48} height={20} className="rounded-full" />
            </div>
            {/* Footer: timestamp + actions */}
            <div className="flex items-center justify-between pt-2">
              <Skeleton variant="line" width={80} height={12} />
              <div className="flex items-center gap-2">
                <Skeleton variant="circle" width={24} height={24} />
                <Skeleton variant="circle" width={24} height={24} />
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

/**
 * Main skeleton component that renders the appropriate variant based on section.
 */
export function DebriefSkeleton({ section }: DebriefSkeletonProps) {
  switch (section) {
    case 'briefings':
      return <BriefingSkeleton />;
    case 'research':
      return <ResearchSkeleton />;
    case 'journal':
      return <JournalSkeleton />;
    default:
      return <BriefingSkeleton />;
  }
}
