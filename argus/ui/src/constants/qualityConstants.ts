/**
 * Shared quality grade constants used across quality UI components.
 *
 * Sprint 24 Session 11f.
 */

/** Canonical grade ordering from highest to lowest. */
export const GRADE_ORDER = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C'] as const;

/** Hex color mapping for quality grades (chart/visualization use). */
export const GRADE_COLORS: Record<string, string> = {
  'A+': '#34d399', // emerald-400
  'A':  '#4ade80', // green-400
  'A-': '#22c55e', // green-500
  'B+': '#fbbf24', // amber-400
  'B':  '#f59e0b', // amber-500
  'B-': '#fb923c', // orange-400
  'C+': '#f87171', // red-400
  'C':  '#9ca3af', // gray-400
};
