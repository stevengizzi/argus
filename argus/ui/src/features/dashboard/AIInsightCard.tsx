/**
 * AI Insight Card for the Dashboard.
 *
 * Displays AI-generated insight about the current trading session.
 * Auto-refreshes during market hours (9:30 AM - 4:00 PM ET).
 *
 * Sprint 22 Session 6.
 */

import { RefreshCw, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { useAIInsight, useAIStatus } from '../../hooks';
import { formatRelativeTime } from '../../utils/format';

/**
 * Skeleton loader for the AI Insight card.
 */
function AIInsightSkeleton() {
  return (
    <Card className="h-full">
      <CardHeader title="AI Insight" />
      <div className="animate-pulse space-y-2">
        <div className="h-4 bg-argus-surface-2 rounded w-full" />
        <div className="h-4 bg-argus-surface-2 rounded w-5/6" />
        <div className="h-4 bg-argus-surface-2 rounded w-3/4" />
      </div>
    </Card>
  );
}

/**
 * Error state for the AI Insight card.
 */
function AIInsightError({ onRetry }: { onRetry: () => void }) {
  return (
    <Card className="h-full">
      <CardHeader
        title="AI Insight"
        icon={<Sparkles className="w-4 h-4 text-argus-accent" />}
      />
      <div className="text-argus-text-dim text-sm">
        Unable to generate insight
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 text-sm text-argus-accent hover:text-argus-accent-bright transition-colors flex items-center gap-1.5"
      >
        <RefreshCw className="w-3.5 h-3.5" />
        Retry
      </button>
    </Card>
  );
}

/**
 * Disabled state when AI services are not available.
 */
function AIInsightDisabled() {
  return (
    <Card className="h-full">
      <CardHeader
        title="AI Insight"
        icon={<Sparkles className="w-4 h-4 text-argus-text-dim" />}
      />
      <div className="text-argus-text-dim text-sm">
        AI insights not available
      </div>
    </Card>
  );
}

export function AIInsightCard() {
  const { data: statusData, isLoading: statusLoading } = useAIStatus();
  const {
    data: insightData,
    isLoading: insightLoading,
    error,
    refetch,
    isFetching,
  } = useAIInsight();

  // Check if AI is disabled
  if (!statusLoading && statusData && !statusData.enabled) {
    return <AIInsightDisabled />;
  }

  // Show skeleton while loading
  if (statusLoading || insightLoading) {
    return <AIInsightSkeleton />;
  }

  // Show error state
  if (error || (insightData && !insightData.insight && insightData.message)) {
    return <AIInsightError onRetry={() => refetch()} />;
  }

  // No data yet
  if (!insightData || !insightData.insight) {
    return <AIInsightSkeleton />;
  }

  const generatedAt = new Date(insightData.generated_at);
  const relativeTime = formatRelativeTime(generatedAt);

  return (
    <Card className="h-full">
      <CardHeader
        title="AI Insight"
        icon={<Sparkles className="w-4 h-4 text-argus-accent" />}
      />

      {/* Insight content with markdown rendering */}
      <div className="prose prose-sm prose-invert max-w-none text-sm text-argus-text leading-relaxed">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeSanitize]}
          components={{
            // Custom paragraph styling
            p: ({ children }) => (
              <p className="my-1 leading-relaxed">{children}</p>
            ),
            // Make code inline styled
            code: ({ children }) => (
              <code className="px-1 py-0.5 bg-argus-bg rounded text-argus-accent font-mono text-xs">
                {children}
              </code>
            ),
            // Style strong text
            strong: ({ children }) => (
              <strong className="text-argus-text font-medium">{children}</strong>
            ),
          }}
        >
          {insightData.insight}
        </ReactMarkdown>
      </div>

      {/* Footer with timestamp and refresh button */}
      <div className="mt-3 flex items-center justify-between text-xs text-argus-text-dim">
        <span>
          Generated {relativeTime}
          {insightData.cached && ' (cached)'}
        </span>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-1 text-argus-accent hover:text-argus-accent-bright transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Refresh insight"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`}
          />
          Refresh
        </button>
      </div>
    </Card>
  );
}
