/**
 * Strategy deployment bar showing capital allocation per strategy.
 *
 * Sprint 21d Code Review Fix #2: Redesign from HeatStripPortfolioBar.
 * - Segments represent capital deployed per STRATEGY (not per position)
 * - Uses strategy accent colors from strategyConfig.ts
 * - "Available" segment in muted dark color for undeployed capital
 * - Labels: strategy letter + dollar amount (wide segments) or just letter (narrow)
 * - Rounded corners only on leftmost/rightmost segments
 * - Tooltip: strategy name, deployed amount, position count, aggregate P&L
 */

import { useState, useRef, useEffect, useMemo } from 'react';
import { usePositions } from '../../hooks/usePositions';
import { useAccount } from '../../hooks/useAccount';
import { formatCurrency } from '../../utils/format';
import { getStrategyDisplay, getStrategyColor, STRATEGY_DISPLAY } from '../../utils/strategyConfig';

/** Height on desktop and mobile */
const BAR_HEIGHT = 24;

/** Width thresholds for label display */
const LABEL_FULL_MIN_WIDTH = 60; // Show letter + amount
const LABEL_LETTER_MIN_WIDTH = 30; // Show just letter

interface TooltipData {
  strategyId: string;
  name: string;
  deployedValue: number;
  positionCount: number;
  aggregatePnl: number;
  x: number;
  y: number;
}

interface StrategySegment {
  strategyId: string;
  name: string;
  letter: string;
  color: string;
  deployedValue: number;
  positionCount: number;
  aggregatePnl: number;
  widthPct: number;
}

interface AvailableSegment {
  strategyId: 'available';
  name: string;
  color: string;
  value: number;
  widthPct: number;
}

type Segment = StrategySegment | AvailableSegment;

export function StrategyDeploymentBar() {
  const { data: positionsData, isLoading: positionsLoading } = usePositions();
  const { data: accountData, isLoading: accountLoading } = useAccount();

  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // Measure container width
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setContainerWidth(entry.contentRect.width);
      }
    });

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Compute segments grouped by strategy
  const segments = useMemo<Segment[]>(() => {
    const equity = accountData?.equity ?? 0;
    if (equity <= 0) return [];

    const positions = positionsData?.positions ?? [];

    // Group positions by strategy
    const strategyMap = new Map<string, {
      deployedValue: number;
      positionCount: number;
      aggregatePnl: number;
    }>();

    for (const pos of positions) {
      const strategyId = pos.strategy_id;
      const posValue = pos.shares_remaining * pos.current_price;
      const existing = strategyMap.get(strategyId);

      if (existing) {
        existing.deployedValue += posValue;
        existing.positionCount += 1;
        existing.aggregatePnl += pos.unrealized_pnl;
      } else {
        strategyMap.set(strategyId, {
          deployedValue: posValue,
          positionCount: 1,
          aggregatePnl: pos.unrealized_pnl,
        });
      }
    }

    // Convert to segment array
    const strategySegments: StrategySegment[] = [];
    let totalDeployed = 0;

    // Use a consistent order based on STRATEGY_DISPLAY keys
    const orderedStrategies = Object.keys(STRATEGY_DISPLAY);

    for (const strategyId of orderedStrategies) {
      const data = strategyMap.get(strategyId);
      if (data && data.deployedValue > 0) {
        const config = getStrategyDisplay(strategyId);
        totalDeployed += data.deployedValue;

        strategySegments.push({
          strategyId,
          name: config.name,
          letter: config.letter,
          color: getStrategyColor(strategyId),
          deployedValue: data.deployedValue,
          positionCount: data.positionCount,
          aggregatePnl: data.aggregatePnl,
          widthPct: (data.deployedValue / equity) * 100,
        });
      }
    }

    // Handle any strategies not in STRATEGY_DISPLAY
    for (const [strategyId, data] of strategyMap) {
      if (!orderedStrategies.includes(strategyId) && data.deployedValue > 0) {
        const config = getStrategyDisplay(strategyId);
        totalDeployed += data.deployedValue;

        strategySegments.push({
          strategyId,
          name: config.name,
          letter: config.letter,
          color: getStrategyColor(strategyId),
          deployedValue: data.deployedValue,
          positionCount: data.positionCount,
          aggregatePnl: data.aggregatePnl,
          widthPct: (data.deployedValue / equity) * 100,
        });
      }
    }

    // Add "Available" segment for undeployed capital
    const availableValue = equity - totalDeployed;
    const allSegments: Segment[] = [...strategySegments];

    if (availableValue > 0) {
      allSegments.push({
        strategyId: 'available',
        name: 'Available',
        color: 'rgba(255, 255, 255, 0.05)',
        value: availableValue,
        widthPct: (availableValue / equity) * 100,
      });
    }

    return allSegments;
  }, [positionsData, accountData]);

  // Determine label type for each segment based on pixel width
  const getLabel = (widthPct: number, segment: Segment): string => {
    const pixelWidth = (widthPct / 100) * containerWidth;

    if (segment.strategyId === 'available') {
      if (pixelWidth >= LABEL_FULL_MIN_WIDTH) return 'Available';
      if (pixelWidth >= LABEL_LETTER_MIN_WIDTH) return '—';
      return '';
    }

    const stratSeg = segment as StrategySegment;
    if (pixelWidth >= LABEL_FULL_MIN_WIDTH) {
      return `${stratSeg.letter} ${formatCurrency(stratSeg.deployedValue, { compact: true })}`;
    }
    if (pixelWidth >= LABEL_LETTER_MIN_WIDTH) {
      return stratSeg.letter;
    }
    return '';
  };

  const handleMouseEnter = (
    segment: Segment,
    event: React.MouseEvent<SVGGElement>
  ) => {
    if (segment.strategyId === 'available') return;

    const stratSeg = segment as StrategySegment;
    const rect = event.currentTarget.getBoundingClientRect();
    setTooltip({
      strategyId: stratSeg.strategyId,
      name: stratSeg.name,
      deployedValue: stratSeg.deployedValue,
      positionCount: stratSeg.positionCount,
      aggregatePnl: stratSeg.aggregatePnl,
      x: rect.left + rect.width / 2,
      y: rect.top,
    });
  };

  const handleMouseLeave = () => {
    setTooltip(null);
  };

  // Loading state
  if (positionsLoading || accountLoading) {
    return (
      <div
        ref={containerRef}
        className="bg-argus-surface-2/30 border border-argus-border/50 rounded-full h-6 animate-pulse"
      />
    );
  }

  // Empty state (no positions, all available)
  if (segments.length === 0 || (segments.length === 1 && segments[0].strategyId === 'available')) {
    return (
      <div
        ref={containerRef}
        className="bg-white/5 border border-argus-border/50 rounded-full h-6 flex items-center justify-center"
        style={{ height: BAR_HEIGHT }}
      >
        <span className="text-xs text-argus-text-dim">No capital deployed</span>
      </div>
    );
  }

  // Compute segment positions
  let xOffset = 0;
  const segmentRects = segments.map((seg, idx) => {
    const x = xOffset;
    xOffset += seg.widthPct;

    const isFirst = idx === 0;
    const isLast = idx === segments.length - 1;

    return { ...seg, x, isFirst, isLast };
  });

  return (
    <div ref={containerRef} className="relative">
      <svg
        width="100%"
        height={BAR_HEIGHT}
        className="block overflow-visible"
        style={{ height: BAR_HEIGHT }}
      >
        {/* Clip path for rounded ends */}
        <defs>
          <clipPath id="bar-clip">
            <rect
              x={0}
              y={0}
              width="100%"
              height={BAR_HEIGHT}
              rx={BAR_HEIGHT / 2}
              ry={BAR_HEIGHT / 2}
            />
          </clipPath>
        </defs>

        {/* Background bar */}
        <rect
          x={0}
          y={0}
          width="100%"
          height={BAR_HEIGHT}
          fill="rgba(255, 255, 255, 0.03)"
          rx={BAR_HEIGHT / 2}
          ry={BAR_HEIGHT / 2}
        />

        {/* Strategy segments - use clip path for rounded ends */}
        <g clipPath="url(#bar-clip)">
          {segmentRects.map((seg) => (
            <g
              key={seg.strategyId}
              className={seg.strategyId !== 'available' ? 'cursor-pointer' : ''}
              onMouseEnter={seg.strategyId !== 'available' ? (e) => handleMouseEnter(seg, e) : undefined}
              onMouseLeave={seg.strategyId !== 'available' ? handleMouseLeave : undefined}
            >
              <rect
                x={`${seg.x}%`}
                y={0}
                width={`${seg.widthPct}%`}
                height={BAR_HEIGHT}
                fill={seg.color}
                className={seg.strategyId !== 'available' ? 'transition-opacity hover:opacity-80' : ''}
              />
              {/* Label */}
              {containerWidth > 0 && getLabel(seg.widthPct, seg) && (
                <text
                  x={`${seg.x + seg.widthPct / 2}%`}
                  y={BAR_HEIGHT / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="fill-white text-xs font-medium pointer-events-none"
                  style={{
                    fontSize: 11,
                    textShadow: '0 1px 2px rgba(0,0,0,0.3)',
                  }}
                >
                  {getLabel(seg.widthPct, seg)}
                </text>
              )}
            </g>
          ))}
        </g>
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 bg-argus-surface border border-argus-border rounded px-2 py-1.5 text-xs shadow-lg pointer-events-none"
          style={{
            left: tooltip.x,
            top: tooltip.y - 8,
            transform: 'translate(-50%, -100%)',
          }}
        >
          <div className="font-medium text-argus-text">{tooltip.name}</div>
          <div className="text-argus-text-dim mt-0.5">
            Deployed: {formatCurrency(tooltip.deployedValue)}
          </div>
          <div className="text-argus-text-dim">
            {tooltip.positionCount} position{tooltip.positionCount !== 1 ? 's' : ''}
          </div>
          <div className={tooltip.aggregatePnl >= 0 ? 'text-argus-profit' : 'text-argus-loss'}>
            P&L: {formatCurrency(tooltip.aggregatePnl)}
          </div>
        </div>
      )}
    </div>
  );
}
