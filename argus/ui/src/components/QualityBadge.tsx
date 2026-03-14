/**
 * Quality grade badge with color-coded pill and hover tooltip.
 *
 * Grade coloring:
 * - A+/A/A- = green shades (high quality setups)
 * - B+/B/B- = amber shades (moderate quality)
 * - C+/C    = red/gray shades (low quality)
 * - No grade = gray placeholder
 *
 * Sprint 24 Session 9.
 */

import type { QualityComponents } from '../api/types';

type GradeColor = { text: string; bg: string };

const GRADE_COLORS: Record<string, GradeColor> = {
  'A+': { text: 'text-emerald-400', bg: 'bg-emerald-400/15' },
  'A':  { text: 'text-green-400', bg: 'bg-green-400/15' },
  'A-': { text: 'text-green-500', bg: 'bg-green-500/15' },
  'B+': { text: 'text-amber-400', bg: 'bg-amber-400/15' },
  'B':  { text: 'text-amber-500', bg: 'bg-amber-500/15' },
  'B-': { text: 'text-orange-400', bg: 'bg-orange-400/15' },
  'C+': { text: 'text-red-400', bg: 'bg-red-400/15' },
  'C':  { text: 'text-gray-400', bg: 'bg-gray-400/15' },
};

const COMPONENT_LABELS: Record<string, string> = {
  ps: 'Pattern Strength',
  cq: 'Catalyst Quality',
  vp: 'Volume Profile',
  hm: 'Historical Match',
  ra: 'Regime Alignment',
};

function buildTooltip(
  grade: string,
  score?: number,
  riskTier?: string,
): string {
  const parts: string[] = [grade];
  if (score !== undefined) {
    parts[0] = `${grade} (${score.toFixed(1)})`;
  }
  if (riskTier) {
    parts.push(`${riskTier} risk`);
  }
  return parts.join(' \u2014 ');
}

interface QualityBadgeProps {
  grade: string;
  score?: number;
  riskTier?: string;
  components?: QualityComponents;
  compact?: boolean;
}

export function QualityBadge({
  grade,
  score,
  riskTier,
  components,
  compact = true,
}: QualityBadgeProps) {
  // Empty/no grade → gray placeholder
  if (!grade) {
    return (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium text-argus-text-dim bg-argus-surface-2"
        data-testid="quality-badge-empty"
      >
        —
      </span>
    );
  }

  const colors = GRADE_COLORS[grade] ?? { text: 'text-gray-400', bg: 'bg-gray-400/15' };
  const tooltip = buildTooltip(grade, score, riskTier);

  if (compact) {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors.text} ${colors.bg}`}
        title={tooltip}
        data-testid="quality-badge"
      >
        {grade}
      </span>
    );
  }

  // Expanded mode: grade pill + optional component breakdown
  return (
    <div className="space-y-2" data-testid="quality-badge-expanded">
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors.text} ${colors.bg}`}
          title={tooltip}
          data-testid="quality-badge"
        >
          {grade}
        </span>
        {score !== undefined && (
          <span className="text-xs text-argus-text-dim tabular-nums">
            {score.toFixed(1)}
          </span>
        )}
        {riskTier && (
          <span className="text-xs text-argus-text-dim">
            {riskTier} risk
          </span>
        )}
      </div>
      {components && (
        <div className="space-y-1" data-testid="quality-components">
          {Object.entries(COMPONENT_LABELS).map(([key, label]) => {
            const value = components[key as keyof QualityComponents];
            return (
              <div key={key} className="flex items-center gap-2 text-xs">
                <span className="w-28 text-argus-text-dim truncate">{label}</span>
                <div className="flex-1 h-1.5 bg-argus-surface-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${colors.bg.replace('/15', '/60')}`}
                    style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
                  />
                </div>
                <span className="w-8 text-right tabular-nums text-argus-text-dim">
                  {value.toFixed(0)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
