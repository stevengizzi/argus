/**
 * Quality vs. Outcome scatter plot for The Debrief page.
 *
 * X-axis: composite quality score (0-100).
 * Y-axis: outcome R-multiple.
 * Each dot colored by quality grade (matching QualityBadge colors).
 * Simple linear regression trend line overlay.
 *
 * Sprint 24 Session 11.
 */

import { useMemo } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  Line,
} from 'recharts';
import { Card } from '../../components/Card';
import { useQualityHistory } from '../../hooks/useQuality';
import type { QualityScoreResponse } from '../../api/types';

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

interface ScatterPoint {
  score: number;
  rMultiple: number;
  grade: string;
  symbol: string;
  color: string;
}

function linearRegression(points: ScatterPoint[]): { slope: number; intercept: number } | null {
  if (points.length < 2) return null;

  const n = points.length;
  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumXX = 0;

  for (const p of points) {
    sumX += p.score;
    sumY += p.rMultiple;
    sumXY += p.score * p.rMultiple;
    sumXX += p.score * p.score;
  }

  const denom = n * sumXX - sumX * sumX;
  if (Math.abs(denom) < 1e-10) return null;

  const slope = (n * sumXY - sumX * sumY) / denom;
  const intercept = (sumY - slope * sumX) / n;

  return { slope, intercept };
}

function buildTrendLineData(
  regression: { slope: number; intercept: number },
  minX: number,
  maxX: number,
): Array<{ score: number; trend: number }> {
  return [
    { score: minX, trend: regression.slope * minX + regression.intercept },
    { score: maxX, trend: regression.slope * maxX + regression.intercept },
  ];
}

export function QualityOutcomeScatter() {
  const { data, isLoading } = useQualityHistory({ limit: 200 });

  const { points, trendLine } = useMemo(() => {
    if (!data?.items) return { points: [], trendLine: null };

    const filtered = data.items.filter(
      (item: QualityScoreResponse) => item.outcome_r_multiple !== null,
    );

    const pts: ScatterPoint[] = filtered.map((item: QualityScoreResponse) => ({
      score: item.score,
      rMultiple: item.outcome_r_multiple as number,
      grade: item.grade,
      symbol: item.symbol,
      color: GRADE_COLORS[item.grade] ?? '#6b7280',
    }));

    const regression = linearRegression(pts);
    let trend: Array<{ score: number; trend: number }> | null = null;

    if (regression && pts.length >= 3) {
      const scores = pts.map((p) => p.score);
      const minX = Math.min(...scores);
      const maxX = Math.max(...scores);
      trend = buildTrendLineData(regression, minX, maxX);
    }

    return { points: pts, trendLine: trend };
  }, [data?.items]);

  if (isLoading) {
    return (
      <Card>
        <h3 className="text-sm font-medium text-argus-text mb-3">
          Quality vs. Outcome
        </h3>
        <div
          className="h-[320px] bg-argus-surface-2 rounded animate-pulse"
          data-testid="quality-scatter-skeleton"
        />
      </Card>
    );
  }

  if (points.length === 0) {
    return (
      <Card>
        <h3 className="text-sm font-medium text-argus-text mb-3">
          Quality vs. Outcome
        </h3>
        <div
          className="flex items-center justify-center h-[320px]"
          data-testid="quality-scatter-empty"
        >
          <p className="text-sm text-argus-text-dim text-center max-w-xs">
            Quality vs. outcome data will appear after trades close with quality
            scoring active
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="text-sm font-medium text-argus-text mb-3">
        Quality vs. Outcome
      </h3>
      <div data-testid="quality-scatter-chart">
        <ResponsiveContainer width="100%" height={320}>
          <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
            <XAxis
              dataKey="score"
              type="number"
              domain={[0, 100]}
              name="Quality Score"
              tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
              tickLine={{ stroke: 'rgba(255,255,255,0.2)' }}
              label={{
                value: 'Quality Score',
                position: 'insideBottom',
                offset: -5,
                fill: 'rgba(255,255,255,0.4)',
                fontSize: 10,
              }}
            />
            <YAxis
              dataKey="rMultiple"
              type="number"
              name="R-Multiple"
              tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
              tickLine={{ stroke: 'rgba(255,255,255,0.2)' }}
              label={{
                value: 'R-Multiple',
                angle: -90,
                position: 'insideLeft',
                offset: 10,
                fill: 'rgba(255,255,255,0.4)',
                fontSize: 10,
              }}
            />
            <ReferenceLine
              y={0}
              stroke="rgba(255,255,255,0.3)"
              strokeDasharray="4 4"
            />
            <Tooltip content={<ScatterTooltip />} />
            <Scatter data={points} isAnimationActive={false}>
              {points.map((point, index) => (
                <Cell
                  key={`dot-${index}`}
                  fill={point.color}
                  fillOpacity={0.7}
                  r={5}
                />
              ))}
            </Scatter>
            {trendLine && (
              <Scatter
                data={trendLine}
                dataKey="trend"
                line={{ stroke: '#60a5fa', strokeWidth: 2, strokeDasharray: '6 3' }}
                shape={() => null}
                legendType="none"
                isAnimationActive={false}
              />
            )}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      {trendLine && (
        <p
          className="text-xs text-argus-text-dim text-center mt-1"
          data-testid="quality-scatter-trend-label"
        >
          Dashed line: linear trend ({points.length} trades)
        </p>
      )}
    </Card>
  );
}

interface ScatterTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: ScatterPoint;
  }>;
}

function ScatterTooltip({ active, payload }: ScatterTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const d = payload[0].payload;
  if (!d.symbol) return null;

  return (
    <div className="px-3 py-2 rounded-lg bg-argus-surface-2 border border-argus-border shadow-lg">
      <div className="text-xs space-y-1">
        <div className="text-argus-text font-medium">
          {d.symbol}{' '}
          <span style={{ color: d.color }}>{d.grade}</span>
        </div>
        <div className="text-argus-text-dim">
          Score: <span className="text-argus-text">{d.score.toFixed(1)}</span>
        </div>
        <div className="text-argus-text-dim">
          Outcome:{' '}
          <span className={d.rMultiple >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
            {d.rMultiple >= 0 ? '+' : ''}{d.rMultiple.toFixed(2)}R
          </span>
        </div>
      </div>
    </div>
  );
}
