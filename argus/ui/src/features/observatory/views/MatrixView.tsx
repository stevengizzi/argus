/**
 * Matrix view — full-screen condition heatmap with virtual scrolling.
 *
 * Rows = symbols on the currently-selected tier, sorted by proximity to trigger
 * (most conditions passed at top, then alphabetical tiebreaker). Columns = entry
 * conditions for the relevant strategy. Cells color-coded green (pass) / red
 * (fail) / gray (not applicable).
 *
 * When multiple strategies evaluate symbols at the current tier, groups by
 * strategy with a strategy header row.
 *
 * Virtual scrolling renders only visible rows + buffer for 500+ row performance.
 * Keyboard navigation: Tab/Shift+Tab cycle highlight, Enter selects symbol.
 * Highlight tracks by symbol across re-sorts.
 *
 * Sprint 25, Sessions 5a + 5b.
 */

import { useRef, useState, useCallback, useEffect, useMemo } from 'react';
import type { ObservatoryClosestMissEntry } from '../../../api/types';
import { useMatrixData } from '../hooks/useMatrixData';
import { MatrixRow } from './MatrixRow';

const ROW_HEIGHT = 32;
const BUFFER_ROWS = 8;

interface MatrixViewProps {
  selectedTier: number;
  selectedSymbol: string | null;
  onSelectSymbol: (symbol: string) => void;
  date?: string;
}

function groupByStrategy(
  items: ObservatoryClosestMissEntry[],
): Map<string, ObservatoryClosestMissEntry[]> {
  return items.reduce((groups, item) => {
    const existing = groups.get(item.strategy);
    if (existing) {
      existing.push(item);
    } else {
      groups.set(item.strategy, [item]);
    }
    return groups;
  }, new Map<string, ObservatoryClosestMissEntry[]>());
}

function getColumnNames(items: ObservatoryClosestMissEntry[]): string[] {
  if (items.length === 0) return [];
  return items[0].conditions_detail.map((c) => c.name);
}

export function MatrixView({
  selectedTier,
  selectedSymbol,
  onSelectSymbol,
  date,
}: MatrixViewProps) {
  const {
    rows: sorted,
    isLoading,
    highlightedSymbol,
    setHighlightedSymbol,
  } = useMatrixData({ tierIndex: selectedTier, date });

  const containerRef = useRef<HTMLDivElement>(null);

  // Keyboard navigation: Tab/Shift+Tab cycle, Enter selects
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      if (e.key === 'Tab' && sorted.length > 0) {
        e.preventDefault();
        const direction = e.shiftKey ? -1 : 1;

        if (highlightedSymbol === null) {
          setHighlightedSymbol(sorted[0].symbol);
          onSelectSymbol(sorted[0].symbol);
          return;
        }

        const currentIdx = sorted.findIndex(
          (r) => r.symbol === highlightedSymbol,
        );
        if (currentIdx === -1) {
          setHighlightedSymbol(sorted[0].symbol);
          onSelectSymbol(sorted[0].symbol);
          return;
        }

        const nextIdx =
          (currentIdx + direction + sorted.length) % sorted.length;
        const nextSymbol = sorted[nextIdx].symbol;
        setHighlightedSymbol(nextSymbol);
        onSelectSymbol(nextSymbol);

        // Auto-scroll highlighted row into view
        if (containerRef.current) {
          const row = containerRef.current.querySelector(
            `[data-testid="matrix-row-${nextSymbol}"]`,
          );
          if (row && typeof row.scrollIntoView === 'function') {
            row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
          }
        }
        return;
      }

      if (e.key === 'Enter' && highlightedSymbol !== null) {
        onSelectSymbol(highlightedSymbol);
        return;
      }
    },
    [sorted, highlightedSymbol, setHighlightedSymbol, onSelectSymbol],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center h-full"
        data-testid="matrix-loading"
      >
        <span className="text-xs text-argus-text-dim">
          Loading matrix data…
        </span>
      </div>
    );
  }

  if (sorted.length === 0) {
    return (
      <div
        className="flex items-center justify-center h-full"
        data-testid="matrix-empty"
      >
        <span className="text-sm text-argus-text-dim">
          No symbols at this tier
        </span>
      </div>
    );
  }

  const strategyGroups = groupByStrategy(sorted);
  const hasMultipleStrategies = strategyGroups.size > 1;

  return (
    <div
      ref={containerRef}
      className="h-full overflow-auto"
      data-testid="matrix-view"
    >
      {hasMultipleStrategies ? (
        Array.from(strategyGroups.entries()).map(
          ([strategy, strategyItems]) => {
            const columns = getColumnNames(strategyItems);
            return (
              <div key={strategy} className="mb-4">
                <div
                  className="sticky top-0 z-20 px-3 py-1.5 text-xs font-semibold text-argus-accent bg-argus-surface/90 border-b border-argus-border backdrop-blur-sm"
                  data-testid={`strategy-header-${strategy}`}
                >
                  {strategy}
                </div>
                <VirtualMatrixTable
                  columns={columns}
                  items={strategyItems}
                  selectedSymbol={selectedSymbol}
                  highlightedSymbol={highlightedSymbol}
                  onSelectSymbol={onSelectSymbol}
                />
              </div>
            );
          },
        )
      ) : (
        <VirtualMatrixTable
          columns={getColumnNames(sorted)}
          items={sorted}
          selectedSymbol={selectedSymbol}
          highlightedSymbol={highlightedSymbol}
          onSelectSymbol={onSelectSymbol}
        />
      )}
    </div>
  );
}

interface VirtualMatrixTableProps {
  columns: string[];
  items: ObservatoryClosestMissEntry[];
  selectedSymbol: string | null;
  highlightedSymbol: string | null;
  onSelectSymbol: (symbol: string) => void;
}

function VirtualMatrixTable({
  columns,
  items,
  selectedSymbol,
  highlightedSymbol,
  onSelectSymbol,
}: VirtualMatrixTableProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);

  useEffect(() => {
    const container = scrollContainerRef.current?.parentElement;
    if (!container) return;

    // Observe parent to get available height without circular dependency
    setContainerHeight(container.clientHeight);
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height);
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const handleScroll = useCallback(() => {
    if (scrollContainerRef.current) {
      setScrollTop(scrollContainerRef.current.scrollTop);
    }
  }, []);

  const { startIndex, endIndex, visibleItems } = useMemo(() => {
    const start = Math.max(
      0,
      Math.floor(scrollTop / ROW_HEIGHT) - BUFFER_ROWS,
    );
    const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT);
    const end = Math.min(items.length - 1, start + visibleCount + BUFFER_ROWS * 2);

    return {
      startIndex: start,
      endIndex: end,
      visibleItems: items.slice(start, end + 1),
    };
  }, [items, scrollTop, containerHeight]);

  // For small lists (< 100 rows), skip virtualization overhead
  if (items.length < 100) {
    return (
      <table className="w-full border-collapse" data-testid="matrix-table">
        <MatrixTableHead columns={columns} />
        <tbody>
          {items.map((item) => (
            <MatrixRow
              key={`${item.symbol}-${item.strategy}`}
              symbol={item.symbol}
              conditionsPassed={item.conditions_passed}
              conditionsTotal={item.conditions_total}
              conditions={item.conditions_detail}
              isSelected={selectedSymbol === item.symbol}
              isHighlighted={highlightedSymbol === item.symbol}
              onSelect={onSelectSymbol}
            />
          ))}
        </tbody>
      </table>
    );
  }

  return (
    <div
      ref={scrollContainerRef}
      className="overflow-y-auto h-full"
      onScroll={handleScroll}
      data-testid="matrix-virtual-container"
    >
      <table className="w-full border-collapse" data-testid="matrix-table">
        <MatrixTableHead columns={columns} />
        <tbody>
          {/* Spacer row for rows above visible range */}
          {startIndex > 0 && (
            <tr style={{ height: startIndex * ROW_HEIGHT }} aria-hidden />
          )}
          {visibleItems.map((item) => (
            <MatrixRow
              key={`${item.symbol}-${item.strategy}`}
              symbol={item.symbol}
              conditionsPassed={item.conditions_passed}
              conditionsTotal={item.conditions_total}
              conditions={item.conditions_detail}
              isSelected={selectedSymbol === item.symbol}
              isHighlighted={highlightedSymbol === item.symbol}
              onSelect={onSelectSymbol}
            />
          ))}
          {/* Spacer row for rows below visible range */}
          {endIndex < items.length - 1 && (
            <tr
              style={{
                height: (items.length - 1 - endIndex) * ROW_HEIGHT,
              }}
              aria-hidden
            />
          )}
        </tbody>
      </table>
    </div>
  );
}

function MatrixTableHead({ columns }: { columns: string[] }) {
  return (
    <thead>
      <tr
        className="sticky top-0 z-10 bg-argus-surface/95 backdrop-blur-sm"
        data-testid="matrix-header-row"
      >
        <th className="sticky left-0 z-20 bg-argus-surface px-3 py-2 text-left text-[10px] font-medium text-argus-text-dim uppercase tracking-wider border-b border-r border-argus-border">
          Symbol
        </th>
        <th className="px-3 py-2 text-center text-[10px] font-medium text-argus-text-dim uppercase tracking-wider border-b border-r border-argus-border">
          Score
        </th>
        {columns.map((col) => (
          <th
            key={col}
            className="px-1 py-2 text-center text-[10px] font-medium text-argus-text-dim uppercase tracking-wider border-b border-argus-border whitespace-nowrap"
            data-testid={`matrix-col-${col}`}
          >
            {col}
          </th>
        ))}
      </tr>
    </thead>
  );
}
