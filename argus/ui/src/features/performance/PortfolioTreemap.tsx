/**
 * Portfolio Treemap visualization.
 *
 * Shows open positions as rectangles sized by capital allocation,
 * colored by unrealized P&L percentage.
 *
 * Features:
 * - D3 treemap layout for rectangle sizing
 * - Diverging green-red color scale based on P&L %
 * - Labels: symbol + P&L % (hidden if rectangle too small)
 * - Hover tooltip: full position details
 * - Click: opens SymbolDetailPanel
 * - Responsive: mobile fallback to sorted list
 * - Empty state when no open positions
 */

import { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import { treemap, hierarchy, treemapSquarify } from 'd3-hierarchy';
import { Card } from '../../components/Card';
import { Badge } from '../../components/Badge';
import { usePositions } from '../../hooks/usePositions';
import { useAccount } from '../../hooks/useAccount';
import { useSymbolDetailUI } from '../../stores/symbolDetailUI';
import {
  createDivergingScale,
  getContrastTextColor,
  getLegendColors,
} from '../../utils/colorScales';
import type { Position } from '../../api/types';

// Strategy abbreviation map
const STRATEGY_ABBREV: Record<string, string> = {
  strat_orb_breakout: 'ORB',
  strat_orb_scalp: 'Scalp',
  strat_vwap_reclaim: 'VWAP',
  strat_afternoon_momentum: 'AFTN',
};

interface TreemapNode {
  symbol: string;
  value: number;
  pnlPct: number;
  pnlDollars: number;
  shares: number;
  entryPrice: number;
  currentPrice: number;
  strategyId: string;
}

interface TooltipData extends TreemapNode {
  x: number;
  y: number;
}

export function PortfolioTreemap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  const { data: positionsData, isLoading: positionsLoading } = usePositions();
  const { data: accountData, isLoading: accountLoading } = useAccount();
  const { open: openSymbolDetail } = useSymbolDetailUI();

  // ResizeObserver for responsive sizing
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width } = entry.contentRect;
        // Height based on aspect ratio, min 200, max 400
        const height = Math.min(Math.max(width * 0.5, 200), 400);
        setDimensions({ width, height });
      }
    });

    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, []);

  // Convert positions to treemap data
  const treemapData = useMemo<TreemapNode[]>(() => {
    if (!positionsData?.positions) return [];

    return positionsData.positions.map((pos: Position) => ({
      symbol: pos.symbol,
      value: pos.shares_remaining * pos.current_price,
      pnlPct: pos.unrealized_pnl_pct,
      pnlDollars: pos.unrealized_pnl,
      shares: pos.shares_remaining,
      entryPrice: pos.entry_price,
      currentPrice: pos.current_price,
      strategyId: pos.strategy_id,
    }));
  }, [positionsData?.positions]);

  // D3 treemap layout
  const treemapLayout = useMemo(() => {
    if (treemapData.length === 0 || dimensions.width === 0) return [];

    const root = hierarchy({ children: treemapData })
      .sum((d) => (d as TreemapNode).value || 0)
      .sort((a, b) => (b.value || 0) - (a.value || 0));

    const treemapGenerator = treemap<typeof root.data>()
      .size([dimensions.width, dimensions.height])
      .padding(3)
      .tile(treemapSquarify);

    treemapGenerator(root);

    return root.leaves().map((leaf) => ({
      x0: leaf.x0 ?? 0,
      y0: leaf.y0 ?? 0,
      x1: leaf.x1 ?? 0,
      y1: leaf.y1 ?? 0,
      data: leaf.data as TreemapNode,
    }));
  }, [treemapData, dimensions]);

  // Color scale: diverging green-red based on P&L %
  const { colorScale, absMax } = useMemo(() => {
    if (treemapData.length === 0) {
      return { colorScale: createDivergingScale(-5, 5), absMax: 5 };
    }

    const pnlValues = treemapData.map((d) => d.pnlPct);
    const minVal = Math.min(...pnlValues);
    const maxVal = Math.max(...pnlValues);
    const absMaxVal = Math.max(Math.abs(minVal), Math.abs(maxVal), 1);

    return {
      colorScale: createDivergingScale(-absMaxVal, absMaxVal),
      absMax: absMaxVal,
    };
  }, [treemapData]);

  // Handle rectangle click
  const handleClick = useCallback(
    (symbol: string) => {
      openSymbolDetail(symbol);
    },
    [openSymbolDetail]
  );

  // Handle hover
  const handleMouseEnter = useCallback(
    (data: TreemapNode, event: React.MouseEvent<SVGRectElement>) => {
      const rect = event.currentTarget.getBoundingClientRect();
      const containerRect = containerRef.current?.getBoundingClientRect();
      if (containerRect) {
        setTooltip({
          ...data,
          x: rect.left + rect.width / 2 - containerRect.left,
          y: rect.top - containerRect.top - 10,
        });
      }
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  const isLoading = positionsLoading || accountLoading;
  const isEmpty = treemapData.length === 0;
  const isMobile = dimensions.width > 0 && dimensions.width < 400;

  if (isLoading) {
    return (
      <Card>
        <div className="px-4 pt-4 pb-2">
          <h3 className="text-sm font-medium text-argus-text">Portfolio Treemap</h3>
        </div>
        <div className="h-[200px] flex items-center justify-center">
          <div className="text-argus-text-dim">Loading positions...</div>
        </div>
      </Card>
    );
  }

  return (
    <Card noPadding>
      <div className="px-4 pt-4 pb-2">
        <h3 className="text-sm font-medium text-argus-text">Portfolio Treemap</h3>
        <p className="text-xs text-argus-text-dim mt-1">
          Position sizes by capital allocation, colored by P&L %
        </p>
      </div>

      <div ref={containerRef} className="px-4 pb-4 relative">
        {isEmpty ? (
          <div className="h-[200px] flex items-center justify-center">
            <p className="text-argus-text-dim">No open positions</p>
          </div>
        ) : isMobile ? (
          // Mobile fallback: sorted list
          <MobileListFallback
            positions={treemapData}
            colorScale={colorScale}
            onSymbolClick={handleClick}
            totalEquity={accountData?.equity ?? 0}
          />
        ) : (
          // Desktop: SVG treemap
          <>
            <svg
              width={dimensions.width}
              height={dimensions.height}
              className="overflow-visible"
              role="img"
              aria-label="Portfolio treemap showing position allocations"
            >
              {treemapLayout.map((node) => {
                const width = node.x1 - node.x0;
                const height = node.y1 - node.y0;
                const showLabel = width >= 60 && height >= 36;
                const color = colorScale(node.data.pnlPct);

                // Dynamic text color based on background luminance
                const textColor = getContrastTextColor(color);

                return (
                  <g key={node.data.symbol}>
                    <rect
                      x={node.x0}
                      y={node.y0}
                      width={width}
                      height={height}
                      rx={4}
                      fill={color}
                      className="cursor-pointer transition-opacity hover:opacity-80"
                      onClick={() => handleClick(node.data.symbol)}
                      onMouseEnter={(e) => handleMouseEnter(node.data, e)}
                      onMouseLeave={handleMouseLeave}
                    />
                    {showLabel && (
                      <>
                        <text
                          x={node.x0 + width / 2}
                          y={node.y0 + height / 2 - 6}
                          textAnchor="middle"
                          fill={textColor}
                          className="text-xs font-medium pointer-events-none"
                        >
                          {node.data.symbol}
                        </text>
                        <text
                          x={node.x0 + width / 2}
                          y={node.y0 + height / 2 + 10}
                          textAnchor="middle"
                          fill={textColor}
                          className="text-[10px] pointer-events-none"
                        >
                          {node.data.pnlPct >= 0 ? '+' : ''}
                          {node.data.pnlPct.toFixed(1)}%
                        </text>
                      </>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Color scale legend */}
            <div className="flex items-center justify-center gap-2 mt-4">
              <span className="text-xs text-argus-text-dim">Loss</span>
              <div className="flex">
                {getLegendColors(absMax).map((color, i) => (
                  <div
                    key={i}
                    className="w-6 h-4"
                    style={{ backgroundColor: color }}
                  />
                ))}
              </div>
              <span className="text-xs text-argus-text-dim">Profit</span>
            </div>
          </>
        )}

        {/* Tooltip */}
        {tooltip && (
          <div
            className="absolute z-50 px-3 py-2 rounded-lg bg-argus-surface-2 border border-argus-border shadow-lg pointer-events-none"
            style={{
              left: tooltip.x,
              top: tooltip.y,
              transform: 'translate(-50%, -100%)',
            }}
          >
            <div className="text-xs space-y-1">
              <div className="text-argus-text font-medium flex items-center gap-2">
                {tooltip.symbol}
                <Badge variant="muted" size="sm">
                  {STRATEGY_ABBREV[tooltip.strategyId] ?? tooltip.strategyId}
                </Badge>
              </div>
              <div className="text-argus-text-dim">
                Shares: <span className="text-argus-text">{tooltip.shares}</span>
              </div>
              <div className="text-argus-text-dim">
                Value:{' '}
                <span className="text-argus-text">${tooltip.value.toLocaleString()}</span>
              </div>
              <div className="text-argus-text-dim">
                Entry:{' '}
                <span className="text-argus-text">${tooltip.entryPrice.toFixed(2)}</span>
              </div>
              <div className="text-argus-text-dim">
                Current:{' '}
                <span className="text-argus-text">${tooltip.currentPrice.toFixed(2)}</span>
              </div>
              <div className="text-argus-text-dim">
                P&L:{' '}
                <span
                  className={
                    tooltip.pnlDollars >= 0 ? 'text-argus-profit' : 'text-argus-loss'
                  }
                >
                  {tooltip.pnlDollars >= 0 ? '+' : ''}${tooltip.pnlDollars.toFixed(2)} (
                  {tooltip.pnlPct >= 0 ? '+' : ''}
                  {tooltip.pnlPct.toFixed(2)}%)
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

/** Mobile fallback: sorted list of positions */
interface MobileListFallbackProps {
  positions: TreemapNode[];
  colorScale: (value: number) => string;
  onSymbolClick: (symbol: string) => void;
  totalEquity: number;
}

function MobileListFallback({
  positions,
  colorScale,
  onSymbolClick,
  totalEquity,
}: MobileListFallbackProps) {
  // Sort by value descending
  const sorted = [...positions].sort((a, b) => b.value - a.value);
  const maxValue = sorted[0]?.value ?? 1;

  return (
    <div className="space-y-2">
      {sorted.map((pos) => {
        const barWidthPct = (pos.value / maxValue) * 100;
        const allocationPct = totalEquity > 0 ? (pos.value / totalEquity) * 100 : 0;

        return (
          <button
            key={pos.symbol}
            onClick={() => onSymbolClick(pos.symbol)}
            className="w-full flex items-center gap-3 p-2 rounded-lg bg-argus-surface hover:bg-argus-surface-2 transition-colors text-left"
          >
            {/* Symbol */}
            <span className="text-sm font-medium text-argus-text w-16">{pos.symbol}</span>

            {/* Value bar */}
            <div className="flex-1 h-4 bg-argus-surface-2 rounded overflow-hidden">
              <div
                className="h-full rounded transition-all"
                style={{
                  width: `${barWidthPct}%`,
                  backgroundColor: colorScale(pos.pnlPct),
                }}
              />
            </div>

            {/* Allocation % */}
            <span className="text-xs text-argus-text-dim w-12 text-right">
              {allocationPct.toFixed(1)}%
            </span>

            {/* P&L badge */}
            <Badge variant={pos.pnlPct >= 0 ? 'profit' : 'loss'} size="sm">
              {pos.pnlPct >= 0 ? '+' : ''}
              {pos.pnlPct.toFixed(1)}%
            </Badge>
          </button>
        );
      })}
    </div>
  );
}
