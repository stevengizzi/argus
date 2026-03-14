/**
 * Quality distribution mini-card for dashboard grid.
 *
 * Donut/pie chart showing grade distribution using useQualityDistribution().
 * Color segments match QualityBadge grade colors. Center text shows total
 * scored signals count. Empty state when no data.
 *
 * Sprint 24 Session 10.
 */

import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { Card } from '../../components/Card';
import { useQualityDistribution } from '../../hooks/useQuality';

const GRADE_COLORS: Record<string, string> = {
  'A+': '#34d399', // emerald-400
  'A':  '#4ade80', // green-400
  'A-': '#22c55e', // green-500
  'B+': '#fbbf24', // amber-400
  'B':  '#f59e0b', // amber-500
  'B-': '#fb923c', // orange-400
  'C+': '#f87171', // red-400
  'C':  '#9ca3af', // gray-400
};

const GRADE_ORDER = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C'];

interface DonutSegment {
  grade: string;
  count: number;
  color: string;
}

export function QualityDistributionCard() {
  const { data, isLoading } = useQualityDistribution();

  if (isLoading) {
    return (
      <Card fullHeight>
        <div className="flex flex-col items-center justify-center h-full min-h-[160px]">
          <div className="w-24 h-24 rounded-full bg-argus-surface-2 animate-pulse" />
        </div>
      </Card>
    );
  }

  const hasData = data && data.total > 0;

  if (!hasData) {
    return (
      <Card fullHeight>
        <p className="text-xs font-medium text-argus-text-dim uppercase tracking-wider mb-3">
          Quality Distribution
        </p>
        <div
          className="flex flex-col items-center justify-center flex-1 min-h-[120px]"
          data-testid="quality-distribution-empty"
        >
          <p className="text-sm text-argus-text-dim">No quality data yet</p>
        </div>
      </Card>
    );
  }

  const segments: DonutSegment[] = GRADE_ORDER
    .filter(grade => (data.grades[grade] ?? 0) > 0)
    .map(grade => ({
      grade,
      count: data.grades[grade],
      color: GRADE_COLORS[grade] ?? '#6b7280',
    }));

  return (
    <Card fullHeight>
      <p className="text-xs font-medium text-argus-text-dim uppercase tracking-wider mb-1">
        Quality Distribution
      </p>
      <div
        className="relative flex items-center justify-center"
        data-testid="quality-distribution-chart"
      >
        <ResponsiveContainer width="100%" height={140}>
          <PieChart>
            <Pie
              data={segments}
              dataKey="count"
              nameKey="grade"
              cx="50%"
              cy="50%"
              innerRadius={38}
              outerRadius={58}
              paddingAngle={2}
              strokeWidth={0}
            >
              {segments.map(segment => (
                <Cell key={segment.grade} fill={segment.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        {/* Center text overlay */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-2xl font-semibold text-argus-text tabular-nums">
            {data.total}
          </span>
          <span className="text-[10px] text-argus-text-dim uppercase">signals</span>
        </div>
      </div>
      {data.filtered > 0 && (
        <p className="text-xs text-argus-text-dim text-center mt-1">
          {data.filtered} filtered
        </p>
      )}
    </Card>
  );
}
