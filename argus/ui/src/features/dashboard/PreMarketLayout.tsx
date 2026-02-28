/**
 * Pre-market dashboard layout with countdown and placeholder cards.
 *
 * Sprint 21d Session 5 (DEC-204, DEC-213): Pre-market layout.
 * - Renders when market_status === 'pre_market' or ?premarket=true in dev mode
 * - MarketCountdown: live countdown to 9:30 AM ET
 * - SessionSummaryCard: yesterday's trading data
 * - Placeholder cards for upcoming features:
 *   - Ranked Watchlist (Sprint 23)
 *   - Regime Forecast (Sprint 22)
 *   - Catalyst Summary (Sprint 23)
 * - GoalTracker: real data, same as market hours
 */

import { motion } from 'framer-motion';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { Badge } from '../../components/Badge';
import { staggerContainer, staggerItem, staggerItemWithChildren } from '../../utils/motion';
import { MarketCountdown } from './MarketCountdown';
import { SessionSummaryCard } from './SessionSummaryCard';
import { GoalTracker } from './GoalTracker';
import { useIsMultiColumn } from '../../hooks/useMediaQuery';

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
 * Ranked Watchlist placeholder with table header.
 */
function RankedWatchlistPlaceholder() {
  return (
    <Card className="h-full flex flex-col">
      <CardHeader
        title="Ranked Watchlist"
        action={<Badge variant="neutral">Coming</Badge>}
      />

      {/* Empty table header */}
      <div className="flex-1">
        <div className="grid grid-cols-5 gap-2 text-xs text-argus-text-dim border-b border-argus-border/50 pb-2 mb-4">
          <span>Rank</span>
          <span>Symbol</span>
          <span>Gap%</span>
          <span>Catalyst</span>
          <span>Quality</span>
        </div>

        <div className="flex items-center justify-center h-24 text-sm text-argus-text-dim">
          Watchlist data will appear here
        </div>
      </div>

      <div className="text-xs text-argus-text-dim text-center pt-2 border-t border-argus-border/50">
        Pre-Market Intelligence activating Sprint 23
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
          <RankedWatchlistPlaceholder />
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
          <RankedWatchlistPlaceholder />
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
