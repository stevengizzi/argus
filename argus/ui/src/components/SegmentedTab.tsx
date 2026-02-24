/**
 * Segmented tab control with live count badges.
 *
 * Design (17-B from UX Feature Backlog):
 * - Rounded pill container with dark background
 * - Active segment: lighter background with smooth Framer Motion layoutId animation
 * - Count badges: small pill inside segment, colored by context
 * - Touch targets >= 44px on mobile
 * - Responsive: full width on mobile, inline on desktop
 */

import { motion } from 'framer-motion';
import { DURATION } from '../utils/motion';

export interface SegmentedTabSegment {
  label: string;
  count?: number;
  value: string;
  /** Optional: override count badge color (default derives from variant) */
  countVariant?: 'default' | 'success' | 'warning' | 'danger';
}

export interface SegmentedTabProps {
  segments: SegmentedTabSegment[];
  activeValue: string;
  onChange: (value: string) => void;
  size?: 'sm' | 'md';
  /** Unique ID for layoutId animation (required if multiple SegmentedTabs on same page) */
  layoutId?: string;
}

function getCountBadgeClasses(variant?: 'default' | 'success' | 'warning' | 'danger'): string {
  switch (variant) {
    case 'success':
      return 'bg-argus-profit/20 text-argus-profit';
    case 'warning':
      return 'bg-argus-warning/20 text-argus-warning';
    case 'danger':
      return 'bg-argus-loss/20 text-argus-loss';
    default:
      return 'bg-argus-surface-3 text-argus-text-dim';
  }
}

export function SegmentedTab({
  segments,
  activeValue,
  onChange,
  size = 'md',
  layoutId = 'segmented-tab',
}: SegmentedTabProps) {
  const sizeClasses = {
    sm: {
      container: 'p-0.5 gap-0.5',
      button: 'px-2.5 py-1.5 text-xs min-h-[36px]',
      badge: 'ml-1.5 px-1.5 py-0.5 text-[10px]',
    },
    md: {
      container: 'p-1 gap-1',
      button: 'px-3 py-2 text-sm min-h-[44px]',
      badge: 'ml-2 px-2 py-0.5 text-xs',
    },
  };

  const classes = sizeClasses[size];

  return (
    <div
      className={`
        inline-flex w-full sm:w-auto
        bg-argus-surface-2 rounded-lg border border-argus-border
        ${classes.container}
      `}
      role="tablist"
    >
      {segments.map((segment) => {
        const isActive = segment.value === activeValue;

        return (
          <button
            key={segment.value}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(segment.value)}
            className={`
              relative flex-1 sm:flex-initial
              flex items-center justify-center
              rounded-md font-medium
              transition-colors duration-150
              ${classes.button}
              ${isActive ? 'text-argus-text' : 'text-argus-text-dim hover:text-argus-text'}
            `}
          >
            {/* Active indicator with layoutId animation */}
            {isActive && (
              <motion.div
                layoutId={layoutId}
                className="absolute inset-0 bg-argus-surface rounded-md"
                initial={false}
                transition={{
                  type: 'spring',
                  stiffness: 500,
                  damping: 35,
                  duration: DURATION.normal,
                }}
              />
            )}

            {/* Content */}
            <span className="relative z-10 flex items-center">
              {segment.label}
              {segment.count !== undefined && (
                <span
                  className={`
                    ${classes.badge}
                    rounded-full tabular-nums font-medium
                    ${getCountBadgeClasses(segment.countVariant)}
                  `}
                >
                  {segment.count}
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}
