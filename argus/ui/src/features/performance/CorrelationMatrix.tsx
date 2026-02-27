/**
 * Strategy Correlation Matrix visualization.
 *
 * Shows pairwise correlation between strategy daily returns as an NxN grid.
 *
 * Features:
 * - D3 scaleSequential with interpolateRdBu for color (-1 to +1)
 * - Diagonal cells: always 1.0, darker shade
 * - Cell labels: correlation coefficient (2 decimal places)
 * - Row/column headers: strategy short names
 * - Hover tooltip: interpretation of correlation strength
 * - Interpretation helper below matrix
 * - Empty state when insufficient data
 */

import { useState, useMemo, useCallback } from 'react';
import { scaleSequential } from 'd3-scale';
import { interpolateRdBu } from 'd3-scale-chromatic';
import { Card } from '../../components/Card';
import { useCorrelation } from '../../hooks/useCorrelation';
import type { PerformancePeriod } from '../../api/types';

// Strategy name mappings
const STRATEGY_SHORT_NAMES: Record<string, string> = {
  strat_orb_breakout: 'ORB',
  strat_orb_scalp: 'Scalp',
  strat_vwap_reclaim: 'VWAP',
  strat_afternoon_momentum: 'AFTN',
};

const STRATEGY_FULL_NAMES: Record<string, string> = {
  strat_orb_breakout: 'ORB Breakout',
  strat_orb_scalp: 'ORB Scalp',
  strat_vwap_reclaim: 'VWAP Reclaim',
  strat_afternoon_momentum: 'Afternoon Momentum',
};

// Get interpretation text for correlation value
function getCorrelationInterpretation(value: number): string {
  const absValue = Math.abs(value);
  if (absValue >= 0.7) return 'strong';
  if (absValue >= 0.4) return 'moderate';
  if (absValue >= 0.2) return 'weak';
  return 'very weak';
}

interface TooltipData {
  row: string;
  col: string;
  value: number;
  x: number;
  y: number;
}

interface CorrelationMatrixProps {
  period: PerformancePeriod;
}

export function CorrelationMatrix({ period }: CorrelationMatrixProps) {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  const { data, isLoading, error } = useCorrelation(period);

  // Color scale: blue (-1) to white (0) to red (+1)
  // Note: interpolateRdBu goes red to blue, so we reverse the domain
  const colorScale = useMemo(() => {
    return scaleSequential(interpolateRdBu).domain([1, -1]);
  }, []);

  // Handle cell hover
  const handleMouseEnter = useCallback(
    (row: string, col: string, value: number, event: React.MouseEvent<SVGRectElement>) => {
      const rect = event.currentTarget.getBoundingClientRect();
      const parentRect = event.currentTarget.closest('svg')?.getBoundingClientRect();
      if (parentRect) {
        setTooltip({
          row,
          col,
          value,
          x: rect.left + rect.width / 2 - parentRect.left,
          y: rect.top - parentRect.top - 10,
        });
      }
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  // Grid dimensions
  const CELL_SIZE = 60;
  const LABEL_WIDTH = 60;
  const GAP = 2;

  if (isLoading) {
    return (
      <Card>
        <div className="px-4 pt-4 pb-2">
          <h3 className="text-sm font-medium text-argus-text">Correlation Matrix</h3>
        </div>
        <div className="h-[200px] flex items-center justify-center">
          <div className="text-argus-text-dim">Loading correlation data...</div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <div className="px-4 pt-4 pb-2">
          <h3 className="text-sm font-medium text-argus-text">Correlation Matrix</h3>
        </div>
        <div className="h-[200px] flex items-center justify-center">
          <div className="text-argus-loss">Failed to load correlation data</div>
        </div>
      </Card>
    );
  }

  // Check if we have enough data
  const hasInsufficientData =
    !data || data.strategy_ids.length < 2 || data.data_days < 5 || data.matrix.length === 0;

  if (hasInsufficientData) {
    return (
      <Card>
        <div className="px-4 pt-4 pb-2">
          <h3 className="text-sm font-medium text-argus-text">Correlation Matrix</h3>
        </div>
        <div className="h-[200px] flex items-center justify-center flex-col gap-2">
          <p className="text-argus-text-dim">
            Insufficient data for correlation analysis
          </p>
          <p className="text-xs text-argus-text-dim">
            Need 5+ trading days with at least 2 strategies
          </p>
          {data?.message && (
            <p className="text-xs text-argus-text-dim">{data.message}</p>
          )}
        </div>
      </Card>
    );
  }

  const n = data.strategy_ids.length;
  const gridSize = n * (CELL_SIZE + GAP) - GAP;
  const svgWidth = gridSize + LABEL_WIDTH + 10;
  const svgHeight = gridSize + LABEL_WIDTH + 10;

  return (
    <Card noPadding>
      <div className="px-4 pt-4 pb-2">
        <h3 className="text-sm font-medium text-argus-text">Correlation Matrix</h3>
        <p className="text-xs text-argus-text-dim mt-1">
          Pairwise strategy return correlations ({data.data_days} trading days)
        </p>
      </div>

      <div className="px-4 pb-4 overflow-x-auto relative">
        <svg
          width={svgWidth}
          height={svgHeight}
          className="mx-auto overflow-visible"
          role="img"
          aria-label="Strategy correlation matrix"
        >
          {/* Column headers (top) */}
          <g transform={`translate(${LABEL_WIDTH + 5}, 0)`}>
            {data.strategy_ids.map((strategyId, i) => (
              <text
                key={`col-${strategyId}`}
                x={i * (CELL_SIZE + GAP) + CELL_SIZE / 2}
                y={LABEL_WIDTH - 8}
                textAnchor="middle"
                className="fill-argus-text text-xs font-medium"
              >
                {STRATEGY_SHORT_NAMES[strategyId] ?? strategyId.slice(-4)}
              </text>
            ))}
          </g>

          {/* Row headers (left) */}
          <g transform={`translate(0, ${LABEL_WIDTH + 5})`}>
            {data.strategy_ids.map((strategyId, i) => (
              <text
                key={`row-${strategyId}`}
                x={LABEL_WIDTH - 8}
                y={i * (CELL_SIZE + GAP) + CELL_SIZE / 2 + 4}
                textAnchor="end"
                className="fill-argus-text text-xs font-medium"
              >
                {STRATEGY_SHORT_NAMES[strategyId] ?? strategyId.slice(-4)}
              </text>
            ))}
          </g>

          {/* Matrix cells */}
          <g transform={`translate(${LABEL_WIDTH + 5}, ${LABEL_WIDTH + 5})`}>
            {data.matrix.map((row, rowIdx) =>
              row.map((value, colIdx) => {
                const isDiagonal = rowIdx === colIdx;
                const cellColor = isDiagonal
                  ? 'rgba(59, 130, 246, 0.7)' // Blue for diagonal (self-correlation)
                  : colorScale(value);

                // Text color: white on strong colors, darker on neutral
                const textColor =
                  isDiagonal || Math.abs(value) > 0.4
                    ? '#ffffff'
                    : 'rgba(255, 255, 255, 0.9)';

                return (
                  <g key={`cell-${rowIdx}-${colIdx}`}>
                    <rect
                      x={colIdx * (CELL_SIZE + GAP)}
                      y={rowIdx * (CELL_SIZE + GAP)}
                      width={CELL_SIZE}
                      height={CELL_SIZE}
                      rx={4}
                      fill={cellColor}
                      className="cursor-pointer transition-opacity hover:opacity-80"
                      onMouseEnter={(e) =>
                        handleMouseEnter(
                          data.strategy_ids[rowIdx],
                          data.strategy_ids[colIdx],
                          value,
                          e
                        )
                      }
                      onMouseLeave={handleMouseLeave}
                    />
                    <text
                      x={colIdx * (CELL_SIZE + GAP) + CELL_SIZE / 2}
                      y={rowIdx * (CELL_SIZE + GAP) + CELL_SIZE / 2 + 5}
                      textAnchor="middle"
                      fill={textColor}
                      className="text-sm font-medium pointer-events-none"
                    >
                      {value.toFixed(2)}
                    </text>
                  </g>
                );
              })
            )}
          </g>
        </svg>

        {/* Color scale legend */}
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className="text-xs text-argus-text-dim">-1.0</span>
          <div className="flex">
            {[...Array(7)].map((_, i) => {
              const t = (i - 3) / 3; // -1 to 1
              return (
                <div
                  key={i}
                  className="w-6 h-4"
                  style={{ backgroundColor: colorScale(t) }}
                />
              );
            })}
          </div>
          <span className="text-xs text-argus-text-dim">+1.0</span>
        </div>

        {/* Interpretation helper */}
        <div className="mt-3 text-center">
          <p className="text-xs text-argus-text-dim">
            Low correlations (&lt;0.3) indicate good diversification between strategies
          </p>
        </div>

        {/* Tooltip */}
        {tooltip && (
          <div
            className="absolute z-50 px-3 py-2 rounded-lg bg-argus-surface-2 border border-argus-border shadow-lg pointer-events-none whitespace-nowrap"
            style={{
              left: tooltip.x + LABEL_WIDTH + 5,
              top: tooltip.y + LABEL_WIDTH + 5,
              transform: 'translate(-50%, -100%)',
            }}
          >
            <div className="text-xs space-y-1">
              <div className="text-argus-text font-medium">
                {STRATEGY_FULL_NAMES[tooltip.row] ?? tooltip.row} &harr;{' '}
                {STRATEGY_FULL_NAMES[tooltip.col] ?? tooltip.col}
              </div>
              <div className="text-argus-text-dim">
                Correlation:{' '}
                <span
                  className={
                    Math.abs(tooltip.value) > 0.5
                      ? 'text-amber-400'
                      : 'text-argus-profit'
                  }
                >
                  {tooltip.value >= 0 ? '+' : ''}
                  {tooltip.value.toFixed(3)}
                </span>
              </div>
              <div className="text-argus-text-dim">
                Strength:{' '}
                <span className="text-argus-text">
                  {getCorrelationInterpretation(tooltip.value)} correlation
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
