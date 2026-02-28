/**
 * Risk Waterfall Chart.
 *
 * Shows worst-case risk exposure if all stops hit.
 * Features:
 * - Custom SVG horizontal waterfall chart
 * - One bar per open position, sorted by risk size (largest first)
 * - Bar length proportional to risk amount
 * - Bar color opacity based on % of daily risk limit
 * - Running total stepped line above bars
 * - Labels: symbol name, risk amount, cumulative %
 * - Final marker with total risk summary
 * - Empty state when no open positions
 * - Responsive: horizontally scrollable on mobile
 */

import { useMemo } from 'react';
import { Card } from '../../components/Card';
import { usePositions } from '../../hooks/usePositions';
import { useAccount } from '../../hooks/useAccount';

// Constants for chart layout
const BAR_HEIGHT = 28;
const BAR_GAP = 8;
const LEFT_MARGIN = 80; // Space for symbol labels
const RIGHT_MARGIN = 100; // Space for risk amount labels
const TOP_MARGIN = 30; // Space for running total line
const BOTTOM_MARGIN = 40; // Space for total summary

// Colors
const RISK_COLOR_BASE = '#ef4444'; // Red base
const RUNNING_TOTAL_COLOR = '#f59e0b'; // Amber for running total line

interface PositionRisk {
  symbol: string;
  riskAmount: number;
  riskPct: number; // % of equity
  strategyId: string;
}

interface RiskWaterfallProps {
  /** Fill available height (for matching heights in grid rows) */
  fullHeight?: boolean;
}

export function RiskWaterfall({ fullHeight = false }: RiskWaterfallProps) {
  const { data: positionsData, isLoading: positionsLoading } = usePositions();
  const { data: accountData, isLoading: accountLoading } = useAccount();

  // Calculate risk for each position
  const positionRisks = useMemo<PositionRisk[]>(() => {
    if (!positionsData?.positions || !accountData) return [];

    const risks = positionsData.positions.map((pos) => {
      // Risk = shares × (entry_price - stop_price) for longs
      // For shorts it would be shares × (stop_price - entry_price)
      const isLong = pos.side === 'long';
      const riskPerShare = isLong
        ? pos.entry_price - pos.stop_price
        : pos.stop_price - pos.entry_price;
      const riskAmount = pos.shares_remaining * Math.max(riskPerShare, 0);
      const riskPct = accountData.equity > 0 ? (riskAmount / accountData.equity) * 100 : 0;

      return {
        symbol: pos.symbol,
        riskAmount,
        riskPct,
        strategyId: pos.strategy_id,
      };
    });

    // Sort by risk amount descending (largest first)
    return risks.sort((a, b) => b.riskAmount - a.riskAmount);
  }, [positionsData?.positions, accountData]);

  // Calculate totals
  const totalRisk = useMemo(() => {
    return positionRisks.reduce((sum, p) => sum + p.riskAmount, 0);
  }, [positionRisks]);

  const totalRiskPct = useMemo(() => {
    if (!accountData?.equity) return 0;
    return (totalRisk / accountData.equity) * 100;
  }, [totalRisk, accountData?.equity]);

  // Max risk for scaling bars
  const maxRisk = useMemo(() => {
    if (positionRisks.length === 0) return 1;
    return Math.max(...positionRisks.map((p) => p.riskAmount), 1);
  }, [positionRisks]);

  // Cumulative risks for running total line
  const cumulativeRisks = useMemo(() => {
    let cumulative = 0;
    return positionRisks.map((p) => {
      cumulative += p.riskAmount;
      return cumulative;
    });
  }, [positionRisks]);

  const isLoading = positionsLoading || accountLoading;

  if (isLoading) {
    return (
      <Card fullHeight={fullHeight}>
        <div className="px-4 pt-4 pb-2">
          <h3 className="text-sm font-medium text-argus-text">Risk Waterfall</h3>
        </div>
        <div className="flex-grow flex items-center justify-center min-h-[200px]">
          <div className="text-argus-text-dim">Loading positions...</div>
        </div>
      </Card>
    );
  }

  const isEmpty = positionRisks.length === 0;

  // Calculate SVG dimensions
  const chartWidth = 500; // Base width, will be constrained by ResponsiveContainer
  const barAreaWidth = chartWidth - LEFT_MARGIN - RIGHT_MARGIN;
  const chartHeight = isEmpty
    ? 100
    : TOP_MARGIN + positionRisks.length * (BAR_HEIGHT + BAR_GAP) + BOTTOM_MARGIN;

  return (
    <Card noPadding fullHeight={fullHeight}>
      <div className="px-4 pt-4 pb-2">
        <h3 className="text-sm font-medium text-argus-text">Risk Waterfall</h3>
        <p className="text-xs text-argus-text-dim mt-1">
          Worst-case scenario if all stops hit
        </p>
      </div>

      <div className="px-4 pb-4 overflow-x-auto flex-grow flex flex-col justify-center">
        {isEmpty ? (
          <div className="min-h-[100px] flex items-center justify-center">
            <p className="text-argus-text-dim">No open positions — zero risk exposure</p>
          </div>
        ) : (
          <svg
            width="100%"
            height={chartHeight}
            viewBox={`0 0 ${chartWidth} ${chartHeight}`}
            preserveAspectRatio="xMidYMid meet"
            role="img"
            aria-label="Risk waterfall chart showing worst-case risk per position"
          >
            {/* Running total stepped line */}
            <g className="running-total">
              {cumulativeRisks.map((cumRisk, i) => {
                const barY = TOP_MARGIN + i * (BAR_HEIGHT + BAR_GAP);
                const barEndY = barY + BAR_HEIGHT;
                const xPos = LEFT_MARGIN + (cumRisk / totalRisk) * barAreaWidth;

                return (
                  <g key={`running-${i}`}>
                    {/* Vertical line from previous level */}
                    {i > 0 && (
                      <line
                        x1={LEFT_MARGIN + (cumulativeRisks[i - 1] / totalRisk) * barAreaWidth}
                        y1={barY}
                        x2={xPos}
                        y2={barY}
                        stroke={RUNNING_TOTAL_COLOR}
                        strokeWidth={2}
                        strokeDasharray="4 2"
                      />
                    )}
                    {/* Horizontal segment */}
                    <line
                      x1={xPos}
                      y1={barY}
                      x2={xPos}
                      y2={barEndY}
                      stroke={RUNNING_TOTAL_COLOR}
                      strokeWidth={2}
                      strokeDasharray="4 2"
                    />
                    {/* Cumulative label (only show for every other or last) */}
                    {(i === positionRisks.length - 1 || i % 2 === 0) && (
                      <text
                        x={xPos}
                        y={barY - 4}
                        textAnchor="middle"
                        className="fill-amber-400 text-[9px]"
                      >
                        {((cumRisk / (accountData?.equity ?? 1)) * 100).toFixed(1)}%
                      </text>
                    )}
                  </g>
                );
              })}
            </g>

            {/* Bars */}
            {positionRisks.map((pos, i) => {
              const barY = TOP_MARGIN + i * (BAR_HEIGHT + BAR_GAP);
              const barWidth = (pos.riskAmount / maxRisk) * barAreaWidth;

              // Opacity based on risk percentage (higher risk = more opaque)
              const opacity = Math.min(0.4 + pos.riskPct * 0.2, 1);

              return (
                <g key={pos.symbol}>
                  {/* Symbol label */}
                  <text
                    x={LEFT_MARGIN - 8}
                    y={barY + BAR_HEIGHT / 2 + 4}
                    textAnchor="end"
                    className="fill-argus-text text-xs font-medium"
                  >
                    {pos.symbol}
                  </text>

                  {/* Risk bar */}
                  <rect
                    x={LEFT_MARGIN}
                    y={barY}
                    width={Math.max(barWidth, 4)}
                    height={BAR_HEIGHT}
                    rx={4}
                    fill={RISK_COLOR_BASE}
                    fillOpacity={opacity}
                    className="transition-all duration-200"
                  />

                  {/* Risk amount label */}
                  <text
                    x={LEFT_MARGIN + barWidth + 8}
                    y={barY + BAR_HEIGHT / 2 + 4}
                    textAnchor="start"
                    className="fill-argus-loss text-xs"
                  >
                    ${pos.riskAmount.toFixed(0)}
                  </text>

                  {/* Risk percentage (small, dimmed) */}
                  <text
                    x={LEFT_MARGIN + barWidth + 60}
                    y={barY + BAR_HEIGHT / 2 + 4}
                    textAnchor="start"
                    className="fill-argus-text-dim text-[10px]"
                  >
                    ({pos.riskPct.toFixed(2)}%)
                  </text>
                </g>
              );
            })}

            {/* Total summary line at bottom */}
            <g transform={`translate(0, ${chartHeight - BOTTOM_MARGIN + 16})`}>
              <line
                x1={LEFT_MARGIN}
                y1={0}
                x2={chartWidth - RIGHT_MARGIN}
                y2={0}
                stroke="rgba(255,255,255,0.2)"
                strokeWidth={1}
              />
              <text
                x={chartWidth / 2}
                y={20}
                textAnchor="middle"
                className="fill-argus-text text-xs font-medium"
              >
                Total risk:{' '}
                <tspan className="fill-argus-loss">
                  ${totalRisk.toFixed(0)}
                </tspan>
                {' '}
                <tspan className="fill-argus-text-dim">
                  ({totalRiskPct.toFixed(2)}% of equity)
                </tspan>
              </text>
            </g>

            {/* Baseline */}
            <line
              x1={LEFT_MARGIN}
              y1={TOP_MARGIN - 4}
              x2={LEFT_MARGIN}
              y2={chartHeight - BOTTOM_MARGIN + 4}
              stroke="rgba(255,255,255,0.3)"
              strokeWidth={1}
            />
          </svg>
        )}
      </div>
    </Card>
  );
}
