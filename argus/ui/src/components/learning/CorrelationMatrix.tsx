/**
 * Correlation Matrix — heatmap of strategy pair correlations.
 *
 * Custom SVG heatmap (Recharts lacks native heatmap support).
 * Blue (negative) → white (zero) → red (positive) color scale.
 * Flagged pairs highlighted with dashed border. Excluded strategies shown grey.
 *
 * Sprint 28, Session 6c.
 */

import { useMemo, useState } from 'react';
import { Card } from '../Card';
import { CardHeader } from '../CardHeader';
import type { CorrelationResult } from '../../api/learningApi';

interface CorrelationMatrixProps {
  correlationResult: CorrelationResult | null;
}

/** Interpolate between blue (negative) → white (zero) → red (positive). */
function correlationColor(value: number): string {
  const clamped = Math.max(-1, Math.min(1, value));
  if (clamped < 0) {
    // Blue scale: -1 = saturated blue, 0 = white
    const intensity = Math.abs(clamped);
    const r = Math.round(255 * (1 - intensity * 0.7));
    const g = Math.round(255 * (1 - intensity * 0.7));
    const b = 255;
    return `rgb(${r}, ${g}, ${b})`;
  }
  // Red scale: 0 = white, 1 = saturated red
  const intensity = clamped;
  const r = 255;
  const g = Math.round(255 * (1 - intensity * 0.7));
  const b = Math.round(255 * (1 - intensity * 0.7));
  return `rgb(${r}, ${g}, ${b})`;
}

/** Build a lookup key for the correlation_matrix Record. */
function pairKey(a: string, b: string): string {
  return `${a}:${b}`;
}

/** Check if a pair is flagged. */
function isFlagged(
  a: string,
  b: string,
  flaggedPairs: [string, string][]
): boolean {
  return flaggedPairs.some(
    ([x, y]) => (x === a && y === b) || (x === b && y === a)
  );
}

/** Shorten strategy name for axis labels. */
function shortenName(name: string): string {
  return name
    .replace(/_strategy$/i, '')
    .replace(/_/g, ' ')
    .split(' ')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

interface TooltipState {
  x: number;
  y: number;
  stratA: string;
  stratB: string;
  value: number;
  flagged: boolean;
}

export function CorrelationMatrix({ correlationResult }: CorrelationMatrixProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  // Extract unique strategy names from pairs
  const strategies = useMemo(() => {
    if (!correlationResult) return [];
    const nameSet = new Set<string>();
    for (const [a, b] of correlationResult.strategy_pairs) {
      nameSet.add(a);
      nameSet.add(b);
    }
    // Also include excluded strategies
    for (const name of correlationResult.excluded_strategies) {
      nameSet.add(name);
    }
    return Array.from(nameSet).sort();
  }, [correlationResult]);

  const excludedSet = useMemo(
    () => new Set(correlationResult?.excluded_strategies ?? []),
    [correlationResult]
  );

  // Requires 2+ strategies
  if (!correlationResult || strategies.length < 2) {
    return (
      <Card>
        <CardHeader title="Strategy Correlation" />
        <div className="text-center py-8" data-testid="correlation-empty">
          <p className="text-argus-text-dim text-sm">
            {!correlationResult
              ? 'Correlation data will appear after the first analysis'
              : 'Requires 2+ strategies for correlation analysis'}
          </p>
        </div>
      </Card>
    );
  }

  const n = strategies.length;
  const cellSize = Math.min(48, Math.max(28, 280 / n));
  const labelWidth = 80;
  const labelHeight = 60;
  const svgWidth = labelWidth + n * cellSize;
  const svgHeight = labelHeight + n * cellSize;
  const matrix = correlationResult.correlation_matrix;
  const flaggedPairs = correlationResult.flagged_pairs;

  return (
    <Card>
      <CardHeader
        title="Strategy Correlation"
        subtitle={`${correlationResult.window_days}d window`}
      />
      <div className="relative overflow-x-auto" data-testid="correlation-matrix">
        <svg
          width={svgWidth}
          height={svgHeight}
          className="mx-auto"
          role="img"
          aria-label="Strategy correlation heatmap"
        >
          {/* Column labels (top) */}
          {strategies.map((name, col) => (
            <text
              key={`col-${name}`}
              x={labelWidth + col * cellSize + cellSize / 2}
              y={labelHeight - 6}
              textAnchor="end"
              fontSize={9}
              fill="var(--color-argus-text-dim, #6b7280)"
              transform={`rotate(-45, ${labelWidth + col * cellSize + cellSize / 2}, ${labelHeight - 6})`}
            >
              {shortenName(name)}
            </text>
          ))}

          {/* Row labels (left) + cells */}
          {strategies.map((rowName, row) => (
            <g key={`row-${rowName}`}>
              {/* Row label */}
              <text
                x={labelWidth - 6}
                y={labelHeight + row * cellSize + cellSize / 2 + 3}
                textAnchor="end"
                fontSize={9}
                fill="var(--color-argus-text-dim, #6b7280)"
              >
                {shortenName(rowName)}
              </text>

              {/* Cells */}
              {strategies.map((colName, col) => {
                const isExcluded =
                  excludedSet.has(rowName) || excludedSet.has(colName);
                const isDiagonal = row === col;

                // Look up correlation value
                const key1 = pairKey(rowName, colName);
                const key2 = pairKey(colName, rowName);
                const value = matrix[key1] ?? matrix[key2] ?? (isDiagonal ? 1 : null);
                const flagged =
                  !isDiagonal && value !== null && isFlagged(rowName, colName, flaggedPairs);

                const cx = labelWidth + col * cellSize;
                const cy = labelHeight + row * cellSize;

                let fill: string;
                if (isExcluded) {
                  fill = 'rgb(75, 85, 99)'; // grey
                } else if (isDiagonal) {
                  fill = 'rgb(55, 65, 81)'; // dark grey for diagonal
                } else if (value !== null) {
                  fill = correlationColor(value);
                } else {
                  fill = 'rgb(55, 65, 81)';
                }

                return (
                  <g key={`cell-${row}-${col}`}>
                    <rect
                      x={cx + 1}
                      y={cy + 1}
                      width={cellSize - 2}
                      height={cellSize - 2}
                      fill={fill}
                      rx={2}
                      className="cursor-pointer"
                      onMouseEnter={(e) => {
                        if (!isDiagonal && value !== null) {
                          const rect = (e.target as SVGRectElement).getBoundingClientRect();
                          setTooltip({
                            x: rect.left + rect.width / 2,
                            y: rect.top,
                            stratA: rowName,
                            stratB: colName,
                            value,
                            flagged,
                          });
                        }
                      }}
                      onMouseLeave={() => setTooltip(null)}
                    />
                    {/* Flagged pair border */}
                    {flagged && (
                      <rect
                        x={cx + 1}
                        y={cy + 1}
                        width={cellSize - 2}
                        height={cellSize - 2}
                        fill="none"
                        stroke="rgb(251, 191, 36)"
                        strokeWidth={2}
                        strokeDasharray="3,2"
                        rx={2}
                        pointerEvents="none"
                      />
                    )}
                    {/* Value text for larger cells */}
                    {!isDiagonal && value !== null && cellSize >= 36 && (
                      <text
                        x={cx + cellSize / 2}
                        y={cy + cellSize / 2 + 3}
                        textAnchor="middle"
                        fontSize={8}
                        fontWeight={500}
                        fill={
                          Math.abs(value) > 0.5
                            ? 'rgb(255, 255, 255)'
                            : 'rgb(31, 41, 55)'
                        }
                        pointerEvents="none"
                      >
                        {value.toFixed(2)}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          ))}
        </svg>

        {/* Color scale legend */}
        <div className="flex items-center justify-center gap-2 mt-3 text-[10px] text-argus-text-dim">
          <span>-1.0</span>
          <div className="flex h-2 w-32 rounded-full overflow-hidden">
            <div className="flex-1 bg-blue-400" />
            <div className="flex-1 bg-blue-200" />
            <div className="flex-1 bg-white" />
            <div className="flex-1 bg-red-200" />
            <div className="flex-1 bg-red-400" />
          </div>
          <span>+1.0</span>
          {flaggedPairs.length > 0 && (
            <span className="ml-2 px-1.5 py-0.5 border border-dashed border-amber-400 rounded text-amber-400">
              flagged
            </span>
          )}
        </div>

        {/* Tooltip */}
        {tooltip && (
          <div
            className="fixed z-50 px-2.5 py-1.5 bg-argus-surface-2 border border-argus-border
              rounded shadow-lg text-xs pointer-events-none"
            style={{
              left: tooltip.x,
              top: tooltip.y - 8,
              transform: 'translate(-50%, -100%)',
            }}
            data-testid="correlation-tooltip"
          >
            <div className="font-medium text-argus-text">
              {shortenName(tooltip.stratA)} × {shortenName(tooltip.stratB)}
            </div>
            <div className="text-argus-text-dim tabular-nums">
              Correlation: {tooltip.value.toFixed(3)}
            </div>
            {tooltip.flagged && (
              <div className="text-amber-400 text-[10px] mt-0.5">
                High correlation flagged
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
