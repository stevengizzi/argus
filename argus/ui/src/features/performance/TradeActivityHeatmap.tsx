/**
 * Trade Activity Heatmap visualization.
 *
 * Shows trade activity by hour (x-axis: 9:30-16:00 in 30-min bins)
 * and day of week (y-axis: Mon-Fri).
 *
 * Features:
 * - Color scale: diverging red-white-green (D3 scaleSequential with interpolateRdYlGn)
 * - Toggle: Color by R-Multiple or P&L
 * - Cell content: trade count
 * - Hover: tooltip with time range, day, count, avg R, net P&L
 * - Click: navigate to /trades with hour/day filter
 * - Responsive sizing based on container width
 */

import { useState, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { scaleDiverging } from 'd3-scale';
import { interpolateRdYlGn } from 'd3-scale-chromatic';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';
import { SegmentedTab } from '../../components/SegmentedTab';
import { useHeatmapData } from '../../hooks/useHeatmapData';
import type { PerformancePeriod, HeatmapCell } from '../../api/types';

// Time bins: 9:30, 10:00, 10:30, ..., 15:30 (13 bins)
const TIME_BINS = [
  '9:30', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30',
  '13:00', '13:30', '14:00', '14:30', '15:00', '15:30',
];

// Day labels
const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

// Color mode options
type ColorMode = 'r_multiple' | 'pnl';

const COLOR_SEGMENTS = [
  { label: 'By R-Multiple', value: 'r_multiple' },
  { label: 'By P&L', value: 'pnl' },
];

interface TradeActivityHeatmapProps {
  period: PerformancePeriod;
}

export function TradeActivityHeatmap({ period }: TradeActivityHeatmapProps) {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const [colorMode, setColorMode] = useState<ColorMode>('r_multiple');
  const [hoveredCell, setHoveredCell] = useState<HeatmapCell | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  const { data, isLoading, error } = useHeatmapData(period);

  // Build a lookup map for cells
  const cellMap = useMemo(() => {
    const map = new Map<string, HeatmapCell>();
    if (data?.cells) {
      for (const cell of data.cells) {
        // Key: "hour-dayOfWeek" (hour is 9-15, dayOfWeek is 0-4)
        const key = `${cell.hour}-${cell.day_of_week}`;
        map.set(key, cell);
      }
    }
    return map;
  }, [data?.cells]);

  // Compute color scale domain based on data
  const colorScale = useMemo(() => {
    if (!data?.cells || data.cells.length === 0) {
      return scaleDiverging(interpolateRdYlGn).domain([-1, 0, 1]);
    }

    const values = data.cells.map((c) =>
      colorMode === 'r_multiple' ? c.avg_r_multiple : c.net_pnl
    );
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);

    // For a diverging scale centered on 0
    const absMax = Math.max(Math.abs(minVal), Math.abs(maxVal), 0.01);

    return scaleDiverging(interpolateRdYlGn).domain([-absMax, 0, absMax]);
  }, [data?.cells, colorMode]);

  // Handle cell click - navigate to trades with filter
  const handleCellClick = useCallback((hour: number, dayOfWeek: number) => {
    navigate(`/trades?hour=${hour}&day=${dayOfWeek}`);
  }, [navigate]);

  // Handle cell hover
  const handleCellHover = useCallback((
    cell: HeatmapCell | null,
    event?: React.MouseEvent<SVGRectElement>
  ) => {
    setHoveredCell(cell);
    if (event && cell) {
      const rect = event.currentTarget.getBoundingClientRect();
      setTooltipPosition({
        x: rect.left + rect.width / 2,
        y: rect.top - 10,
      });
    }
  }, []);

  // Format time bin label
  const getTimeBinLabel = (hour: number): string => {
    // hour 9 = 9:30-10:00, etc.
    const binIndex = hour - 9;
    if (binIndex >= 0 && binIndex < TIME_BINS.length) {
      return TIME_BINS[binIndex];
    }
    return `${hour}:00`;
  };

  // Compute grid dimensions
  const CELL_SIZE = 44; // Minimum 44px for touch targets
  const LABEL_WIDTH = 40;
  const LABEL_HEIGHT = 24;
  const GAP = 2;

  const gridWidth = TIME_BINS.length * (CELL_SIZE + GAP) - GAP;
  const gridHeight = DAY_LABELS.length * (CELL_SIZE + GAP) - GAP;
  const svgWidth = gridWidth + LABEL_WIDTH + 10;
  const svgHeight = gridHeight + LABEL_HEIGHT + 10;

  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Trade Activity Heatmap" />
        <div className="h-[280px] flex items-center justify-center">
          <div className="text-argus-text-dim">Loading heatmap data...</div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader title="Trade Activity Heatmap" />
        <div className="h-[280px] flex items-center justify-center">
          <div className="text-argus-loss">Failed to load heatmap data</div>
        </div>
      </Card>
    );
  }

  const isEmpty = !data?.cells || data.cells.length === 0;

  return (
    <Card>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 px-4 pt-4 pb-2">
        <h3 className="text-sm font-medium text-argus-text">Trade Activity Heatmap</h3>
        <SegmentedTab
          segments={COLOR_SEGMENTS}
          activeValue={colorMode}
          onChange={(v) => setColorMode(v as ColorMode)}
          size="sm"
          layoutId="heatmap-color-mode"
        />
      </div>

      <div
        ref={containerRef}
        className="p-4 overflow-x-auto"
      >
        {isEmpty ? (
          <div className="h-[200px] flex items-center justify-center">
            <p className="text-argus-text-dim">No trades in this period</p>
          </div>
        ) : (
          <div className="relative">
            <svg
              width={svgWidth}
              height={svgHeight}
              className="mx-auto"
              role="img"
              aria-label="Trade activity heatmap"
            >
              {/* X-axis labels (time bins) */}
              <g transform={`translate(${LABEL_WIDTH + 5}, 0)`}>
                {TIME_BINS.map((label, i) => (
                  <text
                    key={`x-${i}`}
                    x={i * (CELL_SIZE + GAP) + CELL_SIZE / 2}
                    y={LABEL_HEIGHT - 4}
                    textAnchor="middle"
                    className="fill-argus-text-dim text-[10px]"
                  >
                    {label}
                  </text>
                ))}
              </g>

              {/* Y-axis labels (days) */}
              <g transform={`translate(0, ${LABEL_HEIGHT + 5})`}>
                {DAY_LABELS.map((label, i) => (
                  <text
                    key={`y-${i}`}
                    x={LABEL_WIDTH - 4}
                    y={i * (CELL_SIZE + GAP) + CELL_SIZE / 2 + 4}
                    textAnchor="end"
                    className="fill-argus-text-dim text-xs"
                  >
                    {label}
                  </text>
                ))}
              </g>

              {/* Grid cells */}
              <g transform={`translate(${LABEL_WIDTH + 5}, ${LABEL_HEIGHT + 5})`}>
                {DAY_LABELS.map((_, dayIdx) =>
                  TIME_BINS.map((_, hourIdx) => {
                    const hour = hourIdx + 9; // Hours start at 9
                    const key = `${hour}-${dayIdx}`;
                    const cell = cellMap.get(key);

                    const value = cell
                      ? colorMode === 'r_multiple'
                        ? cell.avg_r_multiple
                        : cell.net_pnl
                      : 0;

                    const hasData = cell && cell.trade_count > 0;
                    const fillColor = hasData
                      ? String(colorScale(value))
                      : 'rgba(55, 65, 81, 0.3)'; // gray for empty

                    // Text color: light on dark, dark on light
                    const textColor = hasData && Math.abs(value) > 0.5
                      ? '#ffffff'
                      : 'rgba(255, 255, 255, 0.8)';

                    return (
                      <g key={`${dayIdx}-${hourIdx}`}>
                        <rect
                          x={hourIdx * (CELL_SIZE + GAP)}
                          y={dayIdx * (CELL_SIZE + GAP)}
                          width={CELL_SIZE}
                          height={CELL_SIZE}
                          rx={4}
                          fill={fillColor}
                          className="cursor-pointer transition-opacity hover:opacity-80"
                          onClick={() => hasData && handleCellClick(hour, dayIdx)}
                          onMouseEnter={(e) => hasData && handleCellHover(cell, e)}
                          onMouseLeave={() => handleCellHover(null)}
                        />
                        {hasData && (
                          <text
                            x={hourIdx * (CELL_SIZE + GAP) + CELL_SIZE / 2}
                            y={dayIdx * (CELL_SIZE + GAP) + CELL_SIZE / 2 + 4}
                            textAnchor="middle"
                            fill={textColor}
                            className="text-xs font-medium pointer-events-none"
                          >
                            {cell.trade_count}
                          </text>
                        )}
                      </g>
                    );
                  })
                )}
              </g>
            </svg>

            {/* Color scale legend */}
            <div className="flex items-center justify-center gap-2 mt-4">
              <span className="text-xs text-argus-text-dim">Loss</span>
              <div className="flex">
                {[...Array(7)].map((_, i) => {
                  const t = (i - 3) / 3; // -1 to 1
                  return (
                    <div
                      key={i}
                      className="w-6 h-4"
                      style={{ backgroundColor: String(colorScale(t)) }}
                    />
                  );
                })}
              </div>
              <span className="text-xs text-argus-text-dim">Profit</span>
            </div>
          </div>
        )}
      </div>

      {/* Tooltip */}
      {hoveredCell && (
        <div
          className="fixed z-50 px-3 py-2 rounded-lg bg-argus-surface-2 border border-argus-border shadow-lg pointer-events-none"
          style={{
            left: tooltipPosition.x,
            top: tooltipPosition.y,
            transform: 'translate(-50%, -100%)',
          }}
        >
          <div className="text-xs space-y-1">
            <div className="text-argus-text font-medium">
              {DAY_LABELS[hoveredCell.day_of_week]} {getTimeBinLabel(hoveredCell.hour)}
            </div>
            <div className="text-argus-text-dim">
              Trades: <span className="text-argus-text">{hoveredCell.trade_count}</span>
            </div>
            <div className="text-argus-text-dim">
              Avg R: <span className={hoveredCell.avg_r_multiple >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
                {hoveredCell.avg_r_multiple >= 0 ? '+' : ''}{hoveredCell.avg_r_multiple.toFixed(2)}R
              </span>
            </div>
            <div className="text-argus-text-dim">
              P&L: <span className={hoveredCell.net_pnl >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
                {hoveredCell.net_pnl >= 0 ? '+' : ''}${hoveredCell.net_pnl.toFixed(0)}
              </span>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
