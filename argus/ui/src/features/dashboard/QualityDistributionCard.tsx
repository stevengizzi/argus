/**
 * Quality distribution mini-card for dashboard grid.
 *
 * Donut/pie chart showing grade distribution using useQualityDistribution().
 * Color segments match QualityBadge grade colors. Center text shows total
 * scored signals count. Empty state when no data.
 *
 * Sprint 24 Session 10.
 */

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { Card } from '../../components/Card';
import { useQualityDistribution } from '../../hooks/useQuality';
import { GRADE_COLORS, GRADE_ORDER } from '../../constants/qualityConstants';

interface DonutSegment {
  grade: string;
  count: number;
  color: string;
  total: number;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: DonutSegment }>;
}

function DonutTooltip({ active, payload }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  const { grade, count, color, total } = payload[0].payload;
  const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';
  return (
    <div className="bg-argus-surface border border-argus-border rounded px-3 py-2 shadow-lg">
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
        <span className="text-sm font-medium text-argus-text">{grade}</span>
      </div>
      <p className="text-xs text-argus-text-dim mt-1">
        {count} signal{count !== 1 ? 's' : ''} ({pct}%)
      </p>
    </div>
  );
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

  const segments = GRADE_ORDER
    .filter(grade => (data.grades[grade] ?? 0) > 0)
    .map(grade => ({
      grade,
      count: data.grades[grade],
      color: GRADE_COLORS[grade] ?? '#6b7280',
      total: data.total,
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
            <Tooltip content={<DonutTooltip />} />
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
      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-x-3 gap-y-1 mt-1" data-testid="quality-donut-legend">
        {segments.map(s => (
          <div key={s.grade} className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }} />
            <span className="text-xs text-argus-text-dim">{s.grade}</span>
          </div>
        ))}
      </div>
      {data.filtered > 0 && (
        <p className="text-xs text-argus-text-dim text-center mt-1">
          {data.filtered} filtered
        </p>
      )}
    </Card>
  );
}
