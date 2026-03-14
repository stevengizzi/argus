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

export function SignalQualityPanel() {
  const { data, isLoading } = useQualityDistribution();

  if (isLoading) {
    return (
      <Card fullHeight>
        <p className="text-xs font-medium text-argus-text-dim uppercase tracking-wider mb-3">
          Signal Quality
        </p>
        <div className="h-[180px] bg-argus-surface-2 rounded animate-pulse" />
      </Card>
    );
  }

  const hasData = data && data.total > 0;

  if (!hasData) {
    return (
      <Card fullHeight>
        <p className="text-xs font-medium text-argus-text-dim uppercase tracking-wider mb-3">
          Signal Quality
        </p>
        <div
          className="flex items-center justify-center h-[180px]"
          data-testid="signal-quality-empty"
        >
          <p className="text-sm text-argus-text-dim">No quality data yet</p>
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
      <p className="text-xs font-medium text-argus-text-dim uppercase tracking-wider mb-3">
        Signal Quality
      </p>
      <div data-testid="signal-quality-histogram">
        <ResponsiveContainer width="100%" height={180}>
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
            <Bar dataKey="count" radius={[3, 3, 0, 0]} maxBarSize={28}>
              {bars.map(bar => (
                <Cell key={bar.grade} fill={bar.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p
        className="text-xs text-argus-text-dim mt-2"
        data-testid="signal-quality-counter"
      >
        Signals today: {passed} passed / {data.filtered} filtered
      </p>
    </Card>
  );
}
