/**
 * Heat strip portfolio bar showing open positions as colored segments.
 *
 * Sprint 21d Session 5 (DEC-204): Dashboard heat strip.
 * - Custom SVG horizontal bar, full width
 * - One segment per open position from usePositions()
 * - Segment width = (position_value / total_equity) * total_bar_width
 * - Color: green-to-red gradient based on unrealized P&L %
 * - Hover: tooltip with symbol, P&L, shares, strategy
 * - Click segment: open SymbolDetailPanel
 * - Empty state: gray bar with centered "No open positions" text
 */

import { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePositions } from '../../hooks/usePositions';
import { useAccount } from '../../hooks/useAccount';
import { useSymbolDetailUI } from '../../stores/symbolDetailUI';
import { formatCurrency, formatPercent } from '../../utils/format';
import { getStrategyDisplay } from '../../utils/strategyConfig';
import { DURATION, EASE } from '../../utils/motion';

/** Minimum segment width in pixels */
const MIN_SEGMENT_WIDTH = 20;

/** Height of the bar */
const BAR_HEIGHT = 24;

interface TooltipData {
  symbol: string;
  pnl: number;
  pnlPct: number;
  shares: number;
  strategy: string;
  x: number;
  y: number;
}

interface SegmentData {
  positionId: string;
  symbol: string;
  pnl: number;
  pnlPct: number;
  shares: number;
  strategy: string;
  value: number;
  widthPct: number;
}

/**
 * Get segment color based on unrealized P&L percentage.
 * >+2%: green-500, 0 to +2%: green-300, 0 to -1%: red-300, <-1%: red-500
 */
function getSegmentColor(pnlPct: number): string {
  if (pnlPct > 2) return '#22c55e'; // green-500
  if (pnlPct > 0) return '#86efac'; // green-300
  if (pnlPct > -1) return '#fca5a5'; // red-300
  return '#ef4444'; // red-500
}

export function HeatStripPortfolioBar() {
  const { data: positionsData, isLoading: positionsLoading } = usePositions();
  const { data: accountData, isLoading: accountLoading } = useAccount();
  const { open: openSymbolDetail } = useSymbolDetailUI();

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

  // Compute segments
  const { segments, overflowCount } = useMemo(() => {
    if (!positionsData?.positions.length || !accountData?.equity) {
      return { segments: [], overflowCount: 0 };
    }

    const equity = accountData.equity;
    const positions = positionsData.positions;

    // Compute raw segment data with width percentages
    const rawSegments: SegmentData[] = positions.map((pos) => {
      const value = pos.shares_remaining * pos.current_price;
      const widthPct = (value / equity) * 100;
      return {
        positionId: pos.position_id,
        symbol: pos.symbol,
        pnl: pos.unrealized_pnl,
        pnlPct: pos.unrealized_pnl_pct,
        shares: pos.shares_remaining,
        strategy: pos.strategy_id,
        value,
        widthPct,
      };
    });

    // Sort by value descending (largest positions first)
    rawSegments.sort((a, b) => b.value - a.value);

    // Check if any segments are too small at current container width
    const minWidthPct = containerWidth > 0 ? (MIN_SEGMENT_WIDTH / containerWidth) * 100 : 5;

    const visible: SegmentData[] = [];
    const overflow: SegmentData[] = [];

    for (const seg of rawSegments) {
      if (seg.widthPct >= minWidthPct) {
        visible.push(seg);
      } else {
        overflow.push(seg);
      }
    }

    return {
      segments: visible,
      overflowCount: overflow.length,
    };
  }, [positionsData, accountData, containerWidth]);

  // Total width of visible segments
  const totalVisiblePct = segments.reduce((sum, s) => sum + s.widthPct, 0);

  // Reserve space for overflow indicator if needed
  const overflowWidthPct = overflowCount > 0 ? 5 : 0;
  const scale = totalVisiblePct > 0 ? (100 - overflowWidthPct) / totalVisiblePct : 1;

  // Fixed height for simplicity
  const height = BAR_HEIGHT;

  const handleSegmentClick = (symbol: string) => {
    openSymbolDetail(symbol);
  };

  const handleMouseEnter = (
    segment: SegmentData,
    event: React.MouseEvent<SVGRectElement>
  ) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setTooltip({
      symbol: segment.symbol,
      pnl: segment.pnl,
      pnlPct: segment.pnlPct,
      shares: segment.shares,
      strategy: segment.strategy,
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
        className="bg-argus-surface-2/30 border border-argus-border/50 rounded-lg h-6 animate-pulse"
      />
    );
  }

  // Empty state
  if (!segments.length && overflowCount === 0) {
    return (
      <div
        ref={containerRef}
        className="bg-argus-surface-2/30 border border-argus-border/50 rounded-lg h-6 flex items-center justify-center"
        style={{ height }}
      >
        <span className="text-xs text-argus-text-dim">No open positions</span>
      </div>
    );
  }

  // Compute segment positions
  let xOffset = 0;
  const segmentRects = segments.map((seg, idx) => {
    const width = seg.widthPct * scale;
    const x = xOffset;
    xOffset += width;

    // Round first and last segments
    const isFirst = idx === 0;
    const isLast = idx === segments.length - 1 && overflowCount === 0;

    return { ...seg, x, width, isFirst, isLast };
  });

  // Segment entrance animation variants
  const segmentVariants = {
    hidden: { scaleX: 0, opacity: 0 },
    visible: (i: number) => ({
      scaleX: 1,
      opacity: 1,
      transition: {
        duration: DURATION.normal,
        delay: i * 0.04, // Stagger 40ms between segments
        ease: EASE.out,
      },
    }),
  };

  return (
    <motion.div
      ref={containerRef}
      className="relative"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: DURATION.fast }}
    >
      <svg
        width="100%"
        height={height}
        className="block rounded-lg overflow-hidden"
        style={{ height }}
      >
        {/* Background bar */}
        <rect
          x={0}
          y={0}
          width="100%"
          height={height}
          fill="var(--color-argus-surface-2)"
          opacity={0.3}
          rx={8}
          ry={8}
        />

        {/* Position segments with entrance animation */}
        {segmentRects.map((seg, idx) => (
          <motion.rect
            key={seg.positionId}
            x={`${seg.x}%`}
            y={0}
            width={`${seg.width}%`}
            height={height}
            fill={getSegmentColor(seg.pnlPct)}
            rx={seg.isFirst ? 8 : 0}
            ry={seg.isFirst ? 8 : 0}
            className="cursor-pointer hover:opacity-80"
            style={{ originX: 0 }} // Scale from left edge
            variants={segmentVariants}
            initial="hidden"
            animate="visible"
            custom={idx}
            onClick={() => handleSegmentClick(seg.symbol)}
            onMouseEnter={(e) => handleMouseEnter(seg, e)}
            onMouseLeave={handleMouseLeave}
          />
        ))}

        {/* Overflow indicator */}
        {overflowCount > 0 && (
          <g>
            <rect
              x={`${100 - overflowWidthPct}%`}
              y={0}
              width={`${overflowWidthPct}%`}
              height={height}
              fill="var(--color-argus-surface-2)"
              rx={8}
              ry={8}
            />
            <text
              x={`${100 - overflowWidthPct / 2}%`}
              y={height / 2}
              textAnchor="middle"
              dominantBaseline="central"
              className="fill-argus-text-dim text-xs pointer-events-none"
              fontSize={10}
            >
              +{overflowCount}
            </text>
          </g>
        )}
      </svg>

      {/* Tooltip */}
      <AnimatePresence>
        {tooltip && (
          <motion.div
            className="fixed z-50 bg-argus-surface border border-argus-border rounded px-2 py-1 text-xs shadow-lg pointer-events-none"
            style={{
              left: tooltip.x,
              top: tooltip.y - 8,
              transform: 'translate(-50%, -100%)',
            }}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: DURATION.fast }}
          >
            <div className="font-medium text-argus-text">{tooltip.symbol}</div>
            <div className="text-argus-text-dim">
              {formatCurrency(tooltip.pnl)} ({formatPercent(tooltip.pnlPct)})
            </div>
            <div className="text-argus-text-dim">
              {tooltip.shares} shares · {getStrategyDisplay(tooltip.strategy).shortName}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
