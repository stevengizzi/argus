/**
 * CatalystBadge - Small badge showing catalyst info for a symbol.
 *
 * Displays a compact pill/badge showing:
 * - Catalyst count
 * - Color coded by highest-priority catalyst type
 * - Tooltip on hover showing top catalyst headline
 *
 * Sprint 23.5 Session 5
 */

import type { CatalystItem } from '../hooks/useCatalysts';

interface CatalystBadgeProps {
  catalysts: CatalystItem[];
}

// Catalyst type priority (lower = higher priority)
const catalystTypePriority: Record<string, number> = {
  earnings: 0,
  insider_trade: 1,
  analyst_action: 2,
  sec_filing: 3,
  corporate_event: 4,
  regulatory: 5,
  news_sentiment: 6,
  other: 7,
};

// Color classes for each catalyst type
const catalystTypeColors: Record<string, string> = {
  earnings: 'text-blue-400 bg-blue-400/20',
  insider_trade: 'text-amber-400 bg-amber-400/20',
  analyst_action: 'text-purple-400 bg-purple-400/20',
  sec_filing: 'text-gray-400 bg-gray-400/20',
  corporate_event: 'text-teal-400 bg-teal-400/20',
  regulatory: 'text-red-400 bg-red-400/20',
  news_sentiment: 'text-green-400 bg-green-400/20',
  other: 'text-gray-400 bg-gray-400/20',
};

/**
 * Get the highest-priority catalyst type from a list of catalysts.
 */
function getHighestPriorityCatalystType(catalysts: CatalystItem[]): string {
  if (catalysts.length === 0) return 'other';

  let highestPriority = Infinity;
  let highestType = 'other';

  for (const catalyst of catalysts) {
    const type = catalyst.catalyst_type.toLowerCase();
    const priority = catalystTypePriority[type] ?? catalystTypePriority.other;

    if (priority < highestPriority) {
      highestPriority = priority;
      highestType = type;
    }
  }

  return highestType;
}

/**
 * CatalystBadge component.
 *
 * Renders nothing if no catalysts. Otherwise renders a compact badge
 * with the count, colored by the highest-priority catalyst type.
 */
export function CatalystBadge({ catalysts }: CatalystBadgeProps) {
  // Render nothing if no catalysts
  if (catalysts.length === 0) {
    return null;
  }

  const highestType = getHighestPriorityCatalystType(catalysts);
  const colorClass = catalystTypeColors[highestType] ?? catalystTypeColors.other;
  const topHeadline = catalysts[0]?.headline ?? '';

  return (
    <span
      className={`inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-semibold ${colorClass}`}
      title={topHeadline}
    >
      {catalysts.length}
    </span>
  );
}
