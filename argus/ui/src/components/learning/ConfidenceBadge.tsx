/**
 * Confidence level badge for Learning Loop recommendations.
 *
 * Color mapping:
 * - HIGH = green
 * - MODERATE = amber
 * - LOW = orange
 * - INSUFFICIENT_DATA = gray
 *
 * Sprint 28, Session 6a.
 */

import type { ConfidenceLevel } from '../../api/learningApi';

const CONFIDENCE_STYLES: Record<ConfidenceLevel, { text: string; bg: string; label: string }> = {
  HIGH: { text: 'text-emerald-400', bg: 'bg-emerald-400/15', label: 'High' },
  MODERATE: { text: 'text-amber-400', bg: 'bg-amber-400/15', label: 'Moderate' },
  LOW: { text: 'text-orange-400', bg: 'bg-orange-400/15', label: 'Low' },
  INSUFFICIENT_DATA: { text: 'text-gray-400', bg: 'bg-gray-400/15', label: 'Insufficient Data' },
};

interface ConfidenceBadgeProps {
  confidence: ConfidenceLevel;
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const style = CONFIDENCE_STYLES[confidence] ?? CONFIDENCE_STYLES.INSUFFICIENT_DATA;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${style.text} ${style.bg}`}
      data-testid="confidence-badge"
    >
      {style.label}
    </span>
  );
}
