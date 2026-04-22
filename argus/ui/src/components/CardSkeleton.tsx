/**
 * Card loading skeleton primitive.
 *
 * Audit FIX-12 finding P1-F2-M06 flagged a mix of loading patterns across the
 * Command Center: Skeleton components (TradesPage, BriefingEditor), spinner
 * overlays (UniverseStatusCard), silent null (Debrief sub-sections, Observatory
 * views). Project-knowledge lesson from Sprint 17.5 ("no conditional skeleton /
 * content swaps — always render same DOM structure") is the convention that
 * should win.
 *
 * This primitive is the shared shape for card-shaped loading states: renders
 * the Card chrome (identical outer DOM to the loaded card) with `Skeleton`
 * rows inside. Adopt opportunistically during page touches — no big-bang
 * migration.
 *
 * Usage:
 * ```tsx
 * {isLoading ? <CardSkeleton rows={3} title /> : <MyCard data={data} />}
 * ```
 */

import { Card } from './Card';
import { Skeleton } from './Skeleton';

interface CardSkeletonProps {
  /** Number of skeleton rows to render inside the card body. Defaults to 3. */
  rows?: number;
  /** Render a wider first row as a pseudo-title. Defaults to true. */
  title?: boolean;
  /** Pass-through to the underlying Card. */
  className?: string;
  /** Pass-through to the underlying Card. */
  fullHeight?: boolean;
}

export function CardSkeleton({
  rows = 3,
  title = true,
  className,
  fullHeight,
}: CardSkeletonProps) {
  return (
    <Card className={className} fullHeight={fullHeight}>
      <div className="space-y-3" data-testid="card-skeleton">
        {title && <Skeleton width="40%" height={18} />}
        {Array.from({ length: rows }, (_, i) => (
          <Skeleton key={i} width={i === rows - 1 ? '70%' : '100%'} height={14} />
        ))}
      </div>
    </Card>
  );
}
