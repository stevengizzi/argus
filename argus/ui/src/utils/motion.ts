/**
 * Centralized animation constants and variants for Framer Motion.
 *
 * Design rules (DEC-110):
 * - All animations <500ms
 * - 60fps - never blocks interaction
 * - Framer Motion for orchestration, CSS for micro-interactions
 * - This file is the single source of truth for all timing
 */

import type { Variants, Transition } from 'framer-motion';

// Animation timing constants
export const DURATION = {
  fast: 0.15,
  normal: 0.25,
  slow: 0.4,
} as const;

// Custom easing curves
export const EASE = {
  out: [0.0, 0.0, 0.2, 1.0] as const,        // ease-out (entries)
  inOut: [0.4, 0.0, 0.2, 1.0] as const,      // ease-in-out (transitions)
  spring: { type: 'spring', stiffness: 300, damping: 30 } as const,
} as const;

// Page transition variants
// Exit fades to black (fast ~150ms), then enter fades in from black (normal ~250ms)
// AnimatePresence mode="wait" ensures exit completes before enter starts
export const pageVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.normal, ease: EASE.out } as Transition,
  },
  exit: {
    opacity: 0,
    transition: { duration: DURATION.fast, ease: EASE.inOut } as Transition,
  },
};

// Stagger container - wrap around a list of items
export function staggerContainer(staggerDelay = 0.06): Variants {
  return {
    hidden: {},
    show: {
      transition: {
        staggerChildren: staggerDelay,
      },
    },
  };
}

// Stagger child - apply to each item in a staggered list
export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.normal, ease: EASE.out } as Transition,
  },
};

// Fade in only (no translate) - for charts, large content blocks
export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { duration: DURATION.slow } as Transition,
  },
};

// Card hover (desktop only - apply via whileHover)
export const cardHover = {
  y: -1,
  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
  transition: { duration: DURATION.fast },
};
