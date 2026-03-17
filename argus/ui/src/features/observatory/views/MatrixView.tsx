/**
 * Matrix view — full-screen condition heatmap.
 *
 * Rows = symbols on the currently-selected tier, sorted by proximity to trigger
 * (most conditions passed at top). Columns = entry conditions for the relevant
 * strategy. Cells color-coded green (pass) / red (fail) / gray (not applicable).
 *
 * When multiple strategies evaluate symbols at the current tier, groups by
 * strategy with a strategy header row.
 *
 * Sprint 25, Session 5a.
 */

import { useQuery } from '@tanstack/react-query';
import { getObservatoryClosestMisses } from '../../../api/client';
import type { ObservatoryClosestMissEntry } from '../../../api/types';
import { PIPELINE_TIERS } from '../hooks/useObservatoryKeyboard';
import { MatrixRow } from './MatrixRow';

interface MatrixViewProps {
  selectedTier: number;
  selectedSymbol: string | null;
  onSelectSymbol: (symbol: string) => void;
}

function tierIndexToKey(index: number): string {
  const tier = PIPELINE_TIERS[index];
  return tier.toLowerCase().replace('-', '_');
}

function useClosestMisses(tierIndex: number) {
  const tierKey = tierIndexToKey(tierIndex);
  return useQuery({
    queryKey: ['observatory', 'closest-misses', tierKey],
    queryFn: () => getObservatoryClosestMisses(tierKey, 100),
    refetchInterval: 5_000,
  });
}

function groupByStrategy(
  items: ObservatoryClosestMissEntry[]
): Map<string, ObservatoryClosestMissEntry[]> {
  const groups = new Map<string, ObservatoryClosestMissEntry[]>();
  for (const item of items) {
    const existing = groups.get(item.strategy);
    if (existing) {
      existing.push(item);
    } else {
      groups.set(item.strategy, [item]);
    }
  }
  return groups;
}

function getColumnNames(items: ObservatoryClosestMissEntry[]): string[] {
  if (items.length === 0) return [];
  return items[0].conditions_detail.map((c) => c.name);
}

export function MatrixView({
  selectedTier,
  selectedSymbol,
  onSelectSymbol,
}: MatrixViewProps) {
  const { data, isLoading } = useClosestMisses(selectedTier);

  const items = data?.items ?? [];
  const sorted = [...items].sort(
    (a, b) => b.conditions_passed - a.conditions_passed
  );

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center h-full"
        data-testid="matrix-loading"
      >
        <span className="text-xs text-argus-text-dim">Loading matrix data…</span>
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
      className="h-full overflow-auto"
      data-testid="matrix-view"
    >
      {hasMultipleStrategies ? (
        // Multiple strategies: render grouped tables
        Array.from(strategyGroups.entries()).map(([strategy, strategyItems]) => {
          const columns = getColumnNames(strategyItems);
          return (
            <div key={strategy} className="mb-4">
              <div
                className="sticky top-0 z-20 px-3 py-1.5 text-xs font-semibold text-argus-accent bg-argus-surface/90 border-b border-argus-border backdrop-blur-sm"
                data-testid={`strategy-header-${strategy}`}
              >
                {strategy}
              </div>
              <MatrixTable
                columns={columns}
                items={strategyItems}
                selectedSymbol={selectedSymbol}
                onSelectSymbol={onSelectSymbol}
              />
            </div>
          );
        })
      ) : (
        // Single strategy: render one table
        <MatrixTable
          columns={getColumnNames(sorted)}
          items={sorted}
          selectedSymbol={selectedSymbol}
          onSelectSymbol={onSelectSymbol}
        />
      )}
    </div>
  );
}

interface MatrixTableProps {
  columns: string[];
  items: ObservatoryClosestMissEntry[];
  selectedSymbol: string | null;
  onSelectSymbol: (symbol: string) => void;
}

function MatrixTable({
  columns,
  items,
  selectedSymbol,
  onSelectSymbol,
}: MatrixTableProps) {
  return (
    <table className="w-full border-collapse" data-testid="matrix-table">
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
      <tbody>
        {items.map((item) => (
          <MatrixRow
            key={`${item.symbol}-${item.strategy}`}
            symbol={item.symbol}
            conditionsPassed={item.conditions_passed}
            conditionsTotal={item.conditions_total}
            conditions={item.conditions_detail}
            isSelected={selectedSymbol === item.symbol}
            onSelect={onSelectSymbol}
          />
        ))}
      </tbody>
    </table>
  );
}
