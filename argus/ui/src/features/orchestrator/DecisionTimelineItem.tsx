/**
 * Single decision item in the decision timeline.
 *
 * Displays a decision with:
 * - Timestamp (left column)
 * - Icon by decision type (middle)
 * - Content: rationale text + optional strategy badge (right)
 *
 * Connecting line visual connects items in the timeline.
 */

import {
  Compass,
  PieChart,
  Play,
  Pause,
  ShieldAlert,
  Moon,
  Clock,
} from 'lucide-react';
import { StrategyBadge } from '../../components/Badge';
import type { DecisionInfo } from '../../api/types';

interface DecisionTimelineItemProps {
  decision: DecisionInfo;
  isFirst: boolean;
  isLast: boolean;
}

type DecisionSeverity = 'green' | 'amber' | 'red' | 'blue' | 'gray';

/**
 * Get icon component and severity for a decision type.
 */
function getDecisionDisplay(decisionType: string): {
  Icon: React.ComponentType<{ className?: string }>;
  severity: DecisionSeverity;
} {
  const type = decisionType.toLowerCase();

  if (type === 'regime_classification' || type === 'regime_recheck') {
    return { Icon: Compass, severity: 'blue' };
  }
  if (type === 'allocation') {
    return { Icon: PieChart, severity: 'green' };
  }
  if (type === 'activation' || type === 'strategy_activated') {
    return { Icon: Play, severity: 'green' };
  }
  if (type === 'suspension' || type === 'strategy_suspended') {
    return { Icon: Pause, severity: 'red' };
  }
  if (type === 'throttle' || type === 'throttle_override') {
    return { Icon: ShieldAlert, severity: 'amber' };
  }
  if (type === 'eod_review') {
    return { Icon: Moon, severity: 'gray' };
  }

  return { Icon: Clock, severity: 'gray' };
}

/**
 * Get severity-based styling classes.
 */
function getSeverityClasses(severity: DecisionSeverity): {
  iconClass: string;
  lineClass: string;
  dotClass: string;
} {
  switch (severity) {
    case 'green':
      return {
        iconClass: 'text-argus-profit',
        lineClass: 'border-argus-profit/30',
        dotClass: 'bg-argus-profit',
      };
    case 'amber':
      return {
        iconClass: 'text-amber-400',
        lineClass: 'border-amber-400/30',
        dotClass: 'bg-amber-400',
      };
    case 'red':
      return {
        iconClass: 'text-argus-loss',
        lineClass: 'border-argus-loss/30',
        dotClass: 'bg-argus-loss',
      };
    case 'blue':
      return {
        iconClass: 'text-argus-accent',
        lineClass: 'border-argus-accent/30',
        dotClass: 'bg-argus-accent',
      };
    default:
      return {
        iconClass: 'text-argus-text-dim',
        lineClass: 'border-argus-border',
        dotClass: 'bg-argus-text-dim',
      };
  }
}

/**
 * Format timestamp to "9:25 AM ET" format.
 */
function formatDecisionTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: '2-digit',
  }) + ' ET';
}

export function DecisionTimelineItem({
  decision,
  isFirst,
  isLast,
}: DecisionTimelineItemProps) {
  const { Icon, severity } = getDecisionDisplay(decision.decision_type);
  const { iconClass, lineClass, dotClass } = getSeverityClasses(severity);

  return (
    <div className="flex items-start gap-3 min-h-[48px]">
      {/* Timestamp column */}
      <div className="w-16 shrink-0 text-xs text-argus-text-dim pt-1 tabular-nums">
        {formatDecisionTime(decision.created_at)}
      </div>

      {/* Icon column with connecting line */}
      <div className="relative w-8 shrink-0 flex flex-col items-center">
        {/* Top connector line (hidden for first item) */}
        {!isFirst && (
          <div className={`absolute top-0 w-px h-3 border-l ${lineClass}`} />
        )}

        {/* Icon with dot background */}
        <div className="relative z-10 mt-1">
          <div
            className={`w-6 h-6 rounded-full flex items-center justify-center bg-argus-surface ${iconClass}`}
          >
            <Icon className="w-4 h-4" />
          </div>
          {/* Severity dot */}
          <div
            className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full ${dotClass}`}
          />
        </div>

        {/* Bottom connector line (hidden for last item) */}
        {!isLast && (
          <div
            className={`flex-1 w-px border-l ${lineClass} mt-1`}
            style={{ minHeight: '16px' }}
          />
        )}
      </div>

      {/* Content column */}
      <div className="flex-1 pt-1 pb-3">
        {/* Primary rationale text */}
        <p className="text-sm text-argus-text leading-relaxed">
          {decision.rationale || formatDecisionType(decision.decision_type)}
        </p>

        {/* Strategy badge if applicable */}
        {decision.strategy_id && (
          <div className="mt-1.5">
            <StrategyBadge strategyId={decision.strategy_id} />
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Fallback display for decision type when no rationale provided.
 */
function formatDecisionType(type: string): string {
  return type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
