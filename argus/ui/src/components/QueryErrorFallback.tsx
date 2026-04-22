/**
 * Shared TanStack Query error fallback.
 *
 * Audit FIX-12 finding P1-F2-M05 flagged ad-hoc error UI across TradesPage
 * (inline red text), AIInsightCard / UniverseStatusCard (custom subtrees),
 * DailyPnlCard / Observatory (silent null). This primitive is the shared
 * shape — a compact card that explains the failure, offers a retry, and
 * surfaces the error message in dev for debugging.
 *
 * Adopt opportunistically during page touches — no big-bang migration.
 *
 * Usage:
 * ```tsx
 * const { data, error, refetch } = useQuery(...);
 * if (error) return <QueryErrorFallback error={error} onRetry={refetch} />;
 * ```
 */

import { AlertCircle, RefreshCw } from 'lucide-react';

interface QueryErrorFallbackProps {
  /** The error thrown by the query. */
  error: Error | { message: string };
  /** Invoked when the user clicks the retry button. Usually `refetch` from useQuery. */
  onRetry?: () => void;
  /** Optional label identifying what failed (e.g., "positions", "trades"). */
  label?: string;
  /** Compact layout — no padding, single-line message. */
  compact?: boolean;
}

export function QueryErrorFallback({
  error,
  onRetry,
  label,
  compact = false,
}: QueryErrorFallbackProps) {
  const message = error?.message ?? 'Request failed';

  if (compact) {
    return (
      <div
        className="flex items-center justify-between gap-2 px-3 py-2 rounded-md bg-argus-loss-dim/40 border border-argus-loss/20 text-sm"
        role="alert"
        data-testid="query-error-fallback"
      >
        <span className="flex items-center gap-2 text-argus-loss min-w-0">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span className="truncate">
            {label ? `Failed to load ${label}` : 'Request failed'}
          </span>
        </span>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="flex items-center gap-1 text-xs text-argus-accent hover:underline flex-shrink-0"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className="flex flex-col items-center justify-center py-8 px-4 text-center"
      role="alert"
      data-testid="query-error-fallback"
    >
      <AlertCircle className="w-8 h-8 text-argus-loss mb-3" />
      <p className="text-sm font-medium text-argus-text mb-1">
        {label ? `Failed to load ${label}` : 'Request failed'}
      </p>
      <p className="text-xs text-argus-text-dim mb-4 max-w-md">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-md bg-argus-accent hover:bg-argus-accent/80 text-white font-medium transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          Try again
        </button>
      )}
    </div>
  );
}
