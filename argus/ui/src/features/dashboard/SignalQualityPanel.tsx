/**
 * Signal quality panel for dashboard — grade histogram + filtered counter.
 *
 * Bar chart showing count per quality grade using Recharts. Each bar colored
 * by grade. Below chart: "Signals today: N passed / M filtered" text.
 *
 * Sprint 24 Session 10.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card } from '../../components/Card';
import { useQualityDistribution } from '../../hooks/useQuality';
import { GRADE_COLORS, GRADE_ORDER } from '../../constants/qualityConstants';

interface GradeBar {
  grade: string;
  count: number;
  color: string;
}

interface BarTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: GradeBar }>;
}

function HistogramTooltip({ active, payload }: BarTooltipProps) {
  if (!active || !payload?.length) return null;
  const { grade, count, color } = payload[0].payload;
  return (
    <div className="bg-argus-surface border border-argus-border rounded px-3 py-2 shadow-lg">
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
        <span className="text-sm font-medium text-argus-text">{grade}</span>
      </div>
      <p className="text-xs text-argus-text-dim mt-1">
        {count} signal{count !== 1 ? 's' : ''}
      </p>
    </div>
  );
}

export function SignalQualityPanel() {
  const { data, isLoading } = useQualityDistribution();

  if (isLoading) {
    return (
      <Card fullHeight>
        <div className="flex flex-col h-full">
          <p className="text-xs font-medium text-argus-text-dim uppercase tracking-wider mb-3 flex-shrink-0">
            Signal Quality
          </p>
          <div className="flex-1 min-h-0 bg-argus-surface-2 rounded animate-pulse" />
        </div>
      </Card>
    );
  }

  const hasData = data && data.total > 0;

  if (!hasData) {
    return (
      <Card fullHeight>
        <div className="flex flex-col h-full">
          <p className="text-xs font-medium text-argus-text-dim uppercase tracking-wider mb-3 flex-shrink-0">
            Signal Quality
          </p>
          <div
            className="flex-1 flex items-center justify-center"
            data-testid="signal-quality-empty"
          >
            <p className="text-sm text-argus-text-dim">No quality data yet</p>
          </div>
        </div>
      </Card>
    );
  }

  const bars: GradeBar[] = GRADE_ORDER.map(grade => ({
    grade,
    count: data.grades[grade] ?? 0,
    color: GRADE_COLORS[grade] ?? '#6b7280',
  }));

  const passed = data.total - data.filtered;

  return (
    <Card fullHeight>
      <div className="flex flex-col h-full">
        <p className="text-xs font-medium text-argus-text-dim uppercase tracking-wider mb-3 flex-shrink-0">
          Signal Quality
        </p>
        <div className="flex-1 min-h-0" data-testid="signal-quality-histogram">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={bars} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <XAxis
                dataKey="grade"
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#6b7280', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<HistogramTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} isAnimationActive={false} />
              <Bar dataKey="count" radius={[3, 3, 0, 0]} maxBarSize={28} isAnimationActive={false}>
                {bars.map(bar => (
                  <Cell key={bar.grade} fill={bar.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p
          className="text-xs text-argus-text-dim mt-2 flex-shrink-0"
          data-testid="signal-quality-counter"
        >
          Signals today: {passed} passed / {data.filtered} filtered
        </p>
      </div>
    </Card>
  );
}
