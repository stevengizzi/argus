/**
 * CatalystAlertPanel - Scrolling catalyst alert feed.
 *
 * Displays recent catalysts in a scrollable panel with:
 * - Symbol colored by catalyst type
 * - Quality score badge
 * - Truncated headline
 * - Source icon/label
 * - Relative time
 *
 * Sprint 23.5 Session 5
 */

import { AlertCircle, FileText, Globe, Radio } from 'lucide-react';
import { Card } from './Card';
import { CardHeader } from './CardHeader';
import { useRecentCatalysts, type CatalystItem } from '../hooks/useCatalysts';

// Color classes for catalyst types (used for symbol text)
const catalystTypeTextColors: Record<string, string> = {
  earnings: 'text-blue-400',
  insider_trade: 'text-amber-400',
  analyst_action: 'text-purple-400',
  sec_filing: 'text-gray-400',
  corporate_event: 'text-teal-400',
  regulatory: 'text-red-400',
  news_sentiment: 'text-green-400',
  other: 'text-gray-400',
};

// Quality score color classes
function getQualityScoreColor(score: number): string {
  if (score >= 70) return 'text-argus-profit bg-argus-profit-dim';
  if (score >= 40) return 'text-amber-400 bg-amber-400/15';
  return 'text-gray-400 bg-gray-400/15';
}

// Source icons
function SourceIcon({ source }: { source: string }) {
  const lowerSource = source.toLowerCase();

  if (lowerSource.includes('sec') || lowerSource.includes('edgar')) {
    return <FileText className="w-3 h-3" />;
  }
  if (lowerSource.includes('fmp') || lowerSource.includes('finnhub')) {
    return <Radio className="w-3 h-3" />;
  }
  return <Globe className="w-3 h-3" />;
}

// Format relative time
function formatRelativeTime(isoDate: string): string {
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMinutes < 1) return 'now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

// Truncate headline to ~80 characters
function truncateHeadline(headline: string, maxLength: number = 80): string {
  if (headline.length <= maxLength) return headline;
  return headline.substring(0, maxLength - 3) + '...';
}

interface CatalystAlertItemProps {
  catalyst: CatalystItem;
}

function CatalystAlertItem({ catalyst }: CatalystAlertItemProps) {
  const symbolColor = catalystTypeTextColors[catalyst.catalyst_type.toLowerCase()] ?? 'text-gray-400';
  const qualityColor = getQualityScoreColor(catalyst.quality_score);

  return (
    <div className="px-3 py-2 border-b border-argus-border/50 last:border-b-0 hover:bg-argus-surface-2/50 transition-colors">
      {/* Row 1: Symbol, quality score, time */}
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="flex items-center gap-2">
          <span className={`font-semibold text-sm ${symbolColor}`}>{catalyst.symbol}</span>
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${qualityColor}`}>
            {Math.round(catalyst.quality_score)}
          </span>
        </div>
        <span className="text-[10px] text-argus-text-dim shrink-0">
          {formatRelativeTime(catalyst.published_at)}
        </span>
      </div>

      {/* Row 2: Headline */}
      <p className="text-xs text-argus-text leading-snug mb-1">
        {truncateHeadline(catalyst.headline)}
      </p>

      {/* Row 3: Source */}
      <div className="flex items-center gap-1 text-[10px] text-argus-text-dim">
        <SourceIcon source={catalyst.source} />
        <span>{catalyst.source}</span>
      </div>
    </div>
  );
}

export function CatalystAlertPanel() {
  const { data, isLoading, error, dataUpdatedAt } = useRecentCatalysts(30);

  // Determine live/stale status
  const isStale = dataUpdatedAt ? Date.now() - dataUpdatedAt > 60_000 : false;

  return (
    <div>
      <CardHeader
        title="Catalyst Alerts"
        icon={<AlertCircle className="w-4 h-4" />}
        badge={
          <span
            className={`w-2 h-2 rounded-full ${isStale ? 'bg-amber-400' : 'bg-argus-profit'}`}
            title={isStale ? 'Data may be stale' : 'Live'}
          />
        }
      />
      <Card>
        {/* Scrollable content area */}
        <div className="max-h-[300px] overflow-y-auto -mx-4 -mb-4">
        {isLoading && (
          <div className="flex items-center justify-center h-32">
            <div className="w-5 h-5 border-2 border-argus-accent border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center h-32 px-4 text-center">
            <AlertCircle className="w-8 h-8 text-argus-text-dim mb-2" />
            <p className="text-sm text-argus-text-dim">Unable to load catalysts</p>
          </div>
        )}

        {!isLoading && !error && data?.catalysts.length === 0 && (
          <div className="flex flex-col items-center justify-center h-32 px-4 text-center">
            <Radio className="w-8 h-8 text-argus-text-dim mb-2" />
            <p className="text-sm text-argus-text-dim">No recent catalysts</p>
          </div>
        )}

        {!isLoading && !error && data && data.catalysts.length > 0 && (
          <div>
            {data.catalysts.map((catalyst, index) => (
              <CatalystAlertItem
                key={`${catalyst.symbol}-${catalyst.published_at}-${index}`}
                catalyst={catalyst}
              />
            ))}
          </div>
        )}
        </div>
      </Card>
    </div>
  );
}
