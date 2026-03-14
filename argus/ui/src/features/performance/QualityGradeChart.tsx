/**
 * Quality Grade Performance Chart — grouped bar chart showing performance by grade.
 *
 * X-axis: quality grades (A+ through C+).
 * Bars: avg PnL, win rate, avg R-multiple per grade.
 * Grades with no data show empty bars (not omitted).
 *
 * Sprint 24 Session 11.
 */

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card } from '../../components/Card';
import { useQualityHistory } from '../../hooks/useQuality';
import type { QualityScoreResponse } from '../../api/types';

const GRADE_ORDER = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C'];

const GRADE_COLORS: Record<string, string> = {
  'A+': '#34d399',
  'A':  '#4ade80',
  'A-': '#22c55e',
  'B+': '#fbbf24',
  'B':  '#f59e0b',
  'B-': '#fb923c',
  'C+': '#f87171',
  'C':  '#9ca3af',
};

// Bar colors for the three metrics
const AVG_PNL_COLOR = '#3b82f6';
const WIN_RATE_COLOR = '#22c55e';
const AVG_R_COLOR = '#a78bfa';

interface GradeAggregate {
  grade: string;
  avgPnl: number;
  winRate: number;
  avgR: number;
  count: number;
  color: string;
}

function aggregateByGrade(items: QualityScoreResponse[]): GradeAggregate[] {
  const byGrade = new Map<string, QualityScoreResponse[]>();

  for (const item of items) {
    if (item.outcome_r_multiple === null) continue;
    const existing = byGrade.get(item.grade) ?? [];
    existing.push(item);
    byGrade.set(item.grade, existing);
  }

  return GRADE_ORDER.map((grade) => {
    const gradeItems = byGrade.get(grade) ?? [];
    if (gradeItems.length === 0) {
      return {
        grade,
        avgPnl: 0,
        winRate: 0,
        avgR: 0,
        count: 0,
        color: GRADE_COLORS[grade] ?? '#6b7280',
      };
    }

    const totalPnl = gradeItems.reduce(
      (sum, item) => sum + (item.outcome_realized_pnl ?? 0),
      0,
    );
    const totalR = gradeItems.reduce(
      (sum, item) => sum + (item.outcome_r_multiple ?? 0),
      0,
    );
    const wins = gradeItems.filter(
      (item) => (item.outcome_realized_pnl ?? 0) > 0,
    ).length;

    return {
      grade,
      avgPnl: Math.round(totalPnl / gradeItems.length),
      winRate: Math.round((wins / gradeItems.length) * 100),
      avgR: Number((totalR / gradeItems.length).toFixed(2)),
      count: gradeItems.length,
      color: GRADE_COLORS[grade] ?? '#6b7280',
    };
  });
}

interface QualityGradeChartProps {
  startDate?: string;
  endDate?: string;
}

export function QualityGradeChart({ startDate, endDate }: QualityGradeChartProps) {
  const { data, isLoading } = useQualityHistory({
    start_date: startDate,
    end_date: endDate,
    limit: 200,
  });

  const chartData = useMemo(() => {
    if (!data?.items) return [];
    return aggregateByGrade(data.items);
  }, [data?.items]);

  const hasOutcomeData = chartData.some((d) => d.count > 0);

  if (isLoading) {
    return (
      <Card>
        <h3 className="text-sm font-medium text-argus-text mb-3">
          Performance by Quality Grade
        </h3>
        <div
          className="h-[280px] bg-argus-surface-2 rounded animate-pulse"
          data-testid="quality-grade-chart-skeleton"
        />
      </Card>
    );
  }

  if (!hasOutcomeData) {
    return (
      <Card>
        <h3 className="text-sm font-medium text-argus-text mb-3">
          Performance by Quality Grade
        </h3>
        <div
          className="flex items-center justify-center h-[280px]"
          data-testid="quality-grade-chart-empty"
        >
          <p className="text-sm text-argus-text-dim">
            Grade performance data will appear after trades close with quality scoring active
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="text-sm font-medium text-argus-text mb-3">
        Performance by Quality Grade
      </h3>
      <div data-testid="quality-grade-chart">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart
            data={chartData}
            margin={{ top: 10, right: 20, left: 0, bottom: 5 }}
          >
            <XAxis
              dataKey="grade"
              tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="pnl"
              tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <YAxis
              yAxisId="pct"
              orientation="right"
              tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              domain={[0, 100]}
              width={40}
            />
            <Tooltip content={<GradeTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.6)' }}
            />
            <Bar
              yAxisId="pnl"
              dataKey="avgPnl"
              name="Avg P&L ($)"
              fill={AVG_PNL_COLOR}
              radius={[3, 3, 0, 0]}
              maxBarSize={24}
            />
            <Bar
              yAxisId="pct"
              dataKey="winRate"
              name="Win Rate (%)"
              fill={WIN_RATE_COLOR}
              radius={[3, 3, 0, 0]}
              maxBarSize={24}
            />
            <Bar
              yAxisId="pnl"
              dataKey="avgR"
              name="Avg R"
              fill={AVG_R_COLOR}
              radius={[3, 3, 0, 0]}
              maxBarSize={24}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

interface GradeTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: GradeAggregate;
  }>;
}

function GradeTooltip({ active, payload }: GradeTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const d = payload[0].payload;

  if (d.count === 0) {
    return (
      <div className="px-3 py-2 rounded-lg bg-argus-surface-2 border border-argus-border shadow-lg">
        <div className="text-xs text-argus-text-dim">
          Grade {d.grade}: No closed trades
        </div>
      </div>
    );
  }

  return (
    <div className="px-3 py-2 rounded-lg bg-argus-surface-2 border border-argus-border shadow-lg">
      <div className="text-xs space-y-1">
        <div className="text-argus-text font-medium">
          Grade {d.grade}
          <span className="text-argus-text-dim ml-2">({d.count} trades)</span>
        </div>
        <div className="text-argus-text-dim">
          Avg P&L:{' '}
          <span className={d.avgPnl >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
            {d.avgPnl >= 0 ? '+' : ''}${d.avgPnl}
          </span>
        </div>
        <div className="text-argus-text-dim">
          Win Rate: <span className="text-argus-text">{d.winRate}%</span>
        </div>
        <div className="text-argus-text-dim">
          Avg R:{' '}
          <span className={d.avgR >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
            {d.avgR >= 0 ? '+' : ''}{d.avgR}R
          </span>
        </div>
      </div>
    </div>
  );
}
