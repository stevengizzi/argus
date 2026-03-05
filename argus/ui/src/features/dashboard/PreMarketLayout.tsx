/**
 * Pre-market dashboard layout with countdown and feature cards.
 *
 * Sprint 21d Session 5 (DEC-204, DEC-213): Pre-market layout.
 * Sprint 21.7 Session 3: PreMarketWatchlistPanel replaces placeholder.
 *
 * - Renders when market_status === 'pre_market' or ?premarket=true in dev mode
 * - MarketCountdown: live countdown to 9:30 AM ET
 * - SessionSummaryCard: yesterday's trading data
 * - PreMarketWatchlistPanel: FMP-scanned symbols with gap%, source badge, reason
 * - Placeholder cards for upcoming features:
 *   - Regime Forecast (Sprint 22)
 *   - Catalyst Summary (Sprint 23)
 * - GoalTracker: real data, same as market hours
 */

import { motion } from 'framer-motion';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { Badge } from '../../components/Badge';
import { Skeleton } from '../../components/Skeleton';
import { staggerContainer, staggerItem, staggerItemWithChildren } from '../../utils/motion';
import { MarketCountdown } from './MarketCountdown';
import { SessionSummaryCard } from './SessionSummaryCard';
import { GoalTracker } from './GoalTracker';
import { useIsMultiColumn } from '../../hooks/useMediaQuery';
import { useWatchlist } from '../../hooks/useWatchlist';

/**
 * Placeholder card for upcoming intelligence features.
 */
function PlaceholderCard({
  title,
  sprint,
  description,
  children,
}: {
  title: string;
  sprint: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <Card className="h-full flex flex-col">
      <CardHeader
        title={title}
        action={<Badge variant="neutral">Coming</Badge>}
      />

      <div className="flex-1 flex flex-col items-center justify-center py-6 text-center">
        {children || (
          <div className="text-argus-text-dim text-sm max-w-[200px]">
            {description}
          </div>
        )}
      </div>

      <div className="text-xs text-argus-text-dim text-center mt-auto pt-2 border-t border-argus-border/50">
        {sprint}
      </div>
    </Card>
  );
}

/**
 * Pre-Market Watchlist panel showing FMP-selected symbols.
 * Displays gap%, source badge, and selection reason.
 * Sprint 21.7 Session 3.
 */
function PreMarketWatchlistPanel() {
  const { data, isLoading, isError } = useWatchlist();

  // Determine source badge based on watchlist data
  const hasFmpSource = data?.symbols.some((item) => item.scan_source === 'fmp' || item.scan_source === 'fmp_fallback');
  const sourceBadgeVariant = hasFmpSource ? 'success' : 'neutral';
  const sourceBadgeLabel = hasFmpSource ? 'FMP' : 'Static';

  // Format selection reason to compact display
  const formatReason = (reason: string): string => {
    if (!reason) return '—';
    // Parse "gap_up_3.2%" or "gap_down_1.8%" patterns
    const gapUpMatch = reason.match(/gap_up_?([\d.]+)%?/i);
    if (gapUpMatch) return `↑ ${gapUpMatch[1]}%`;
    const gapDownMatch = reason.match(/gap_down_?([\d.]+)%?/i);
    if (gapDownMatch) return `↓ ${gapDownMatch[1]}%`;
    if (reason.toLowerCase().includes('volume') || reason.toLowerCase() === 'high_volume') return 'Vol';
    return reason.slice(0, 8);
  };

  // Gap% color based on value
  const getGapColor = (gapPct: number): string => {
    if (gapPct > 0) return 'text-argus-profit';
    if (gapPct < 0) return 'text-argus-loss';
    return 'text-argus-text-dim';
  };

  // Generate skeleton rows for loading state
  const skeletonRows = Array.from({ length: 5 }, (_, i) => (
    <tr key={`skeleton-${i}`} className="border-b border-argus-border/30 last:border-b-0">
      <td className="py-2 pr-2">
        <Skeleton variant="line" width={16} height={14} />
      </td>
      <td className="py-2 pr-2">
        <Skeleton variant="line" width={48} height={14} />
      </td>
      <td className="py-2 pr-2">
        <Skeleton variant="line" width={40} height={14} />
      </td>
      <td className="py-2">
        <Skeleton variant="line" width={56} height={14} />
      </td>
    </tr>
  ));

  // Generate data rows
  const dataRows = data?.symbols.map((item, index) => (
    <tr key={item.symbol} className="border-b border-argus-border/30 last:border-b-0">
      <td className="py-2 pr-2 text-xs text-argus-text-dim">{index + 1}</td>
      <td className="py-2 pr-2 text-sm font-semibold text-argus-text">{item.symbol}</td>
      <td className={`py-2 pr-2 text-xs font-medium ${getGapColor(item.gap_pct)}`}>
        {item.gap_pct > 0 ? '+' : ''}{item.gap_pct.toFixed(1)}%
      </td>
      <td className="py-2 text-xs text-argus-text-dim">{formatReason(item.selection_reason)}</td>
    </tr>
  )) ?? [];

  // Empty state rows (maintain same structure)
  const emptyRows = (
    <tr>
      <td colSpan={4} className="py-8 text-center text-sm text-argus-text-dim">
        No symbols selected yet — scan runs before market open
      </td>
    </tr>
  );

  // Error state rows
  const errorRows = (
    <tr>
      <td colSpan={4} className="py-8 text-center text-sm text-argus-loss">
        Failed to load watchlist
      </td>
    </tr>
  );

  // Determine which rows to render
  const tableRows = isLoading
    ? skeletonRows
    : isError
      ? errorRows
      : dataRows.length > 0
        ? dataRows
        : emptyRows;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader
        title="Pre-Market Watchlist"
        action={<Badge variant={sourceBadgeVariant}>{sourceBadgeLabel}</Badge>}
      />

      {/* Table with consistent DOM structure */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-argus-border/50">
              <th className="pb-2 pr-2 text-xs text-argus-text-dim font-normal">#</th>
              <th className="pb-2 pr-2 text-xs text-argus-text-dim font-normal">Symbol</th>
              <th className="pb-2 pr-2 text-xs text-argus-text-dim font-normal">Gap%</th>
              <th className="pb-2 text-xs text-argus-text-dim font-normal">Reason</th>
            </tr>
          </thead>
          <tbody>
            {tableRows}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/**
 * Regime Forecast placeholder with gauge area.
 */
function RegimeForecastPlaceholder() {
  return (
    <Card className="h-full flex flex-col">
      <CardHeader
        title="Regime Forecast"
        action={<Badge variant="neutral">Coming</Badge>}
      />

      <div className="flex-1 flex items-center justify-center py-6">
        {/* Placeholder gauge circle */}
        <div className="w-24 h-24 rounded-full border-4 border-argus-border/30 flex items-center justify-center">
          <span className="text-argus-text-dim text-sm">?</span>
        </div>
      </div>

      <div className="text-xs text-argus-text-dim text-center pt-2 border-t border-argus-border/50">
        AI-powered regime forecast available Sprint 22
      </div>
    </Card>
  );
}

/**
 * Catalyst Summary placeholder.
 */
function CatalystSummaryPlaceholder() {
  return (
    <PlaceholderCard
      title="Catalyst Summary"
      sprint="NLP Catalyst Pipeline activating Sprint 23"
      description="Earnings, news, and SEC filings affecting watchlist symbols will appear here"
    />
  );
}

export function PreMarketLayout() {
  const isMultiColumn = useIsMultiColumn();

  // Mobile: single column stacked layout
  if (!isMultiColumn) {
    return (
      <motion.div
        key="premarket-mobile"
        className="space-y-4"
        variants={staggerContainer(0.08)}
        initial="hidden"
        animate="show"
      >
        <motion.div variants={staggerItem}>
          <Card>
            <MarketCountdown />
          </Card>
        </motion.div>

        <SessionSummaryCard />

        <motion.div variants={staggerItem}>
          <PreMarketWatchlistPanel />
        </motion.div>

        <motion.div variants={staggerItem}>
          <RegimeForecastPlaceholder />
        </motion.div>

        <motion.div variants={staggerItem}>
          <CatalystSummaryPlaceholder />
        </motion.div>

        <motion.div variants={staggerItem}>
          <GoalTracker />
        </motion.div>
      </motion.div>
    );
  }

  // Tablet/Desktop: 2-column grid layout
  return (
    <motion.div
      key="premarket-desktop"
      className="space-y-6"
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      {/* Countdown hero */}
      <motion.div variants={staggerItem}>
        <Card>
          <MarketCountdown />
        </Card>
      </motion.div>

      {/* Yesterday's session summary */}
      <SessionSummaryCard />

      {/* 2-column grid: Watchlist | Regime */}
      <motion.div
        className="grid grid-cols-2 gap-6"
        variants={staggerItemWithChildren(0.08)}
      >
        <motion.div variants={staggerItem} className="h-full">
          <PreMarketWatchlistPanel />
        </motion.div>
        <motion.div variants={staggerItem} className="h-full">
          <RegimeForecastPlaceholder />
        </motion.div>
      </motion.div>

      {/* 2-column grid: Catalyst | GoalTracker */}
      <motion.div
        className="grid grid-cols-2 gap-6"
        variants={staggerItemWithChildren(0.08)}
      >
        <motion.div variants={staggerItem} className="h-full">
          <CatalystSummaryPlaceholder />
        </motion.div>
        <motion.div variants={staggerItem} className="h-full">
          <GoalTracker />
        </motion.div>
      </motion.div>
    </motion.div>
  );
}
