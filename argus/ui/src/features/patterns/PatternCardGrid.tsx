/**
 * Container for the Pattern Library card grid.
 *
 * Applies filters and sorting from the UI store, then renders
 * PatternFilters and a grid of PatternCards.
 */

import { useMemo } from 'react';
import { Filter } from 'lucide-react';
import { usePatternLibraryUI } from '../../stores/patternLibraryUI';
import { EmptyState } from '../../components/EmptyState';
import { PatternFilters } from './PatternFilters';
import { PatternCard } from './PatternCard';
import type { StrategyInfo } from '../../api/types';

interface PatternCardGridProps {
  strategies: StrategyInfo[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

/**
 * Classify a time window string as 'morning' or 'afternoon'.
 *
 * Logic: Check START time first (before dash), then fall back to END time if needed.
 * - "9:35–11:30 AM"    → start="9:35" (no AM/PM), end="11:30 AM" (AM) → morning
 * - "10:00 AM–12:00 PM" → start="10:00 AM" (AM) → morning
 * - "2:00–3:30 PM"      → start="2:00" (no AM/PM), end="3:30 PM" (PM) → afternoon
 */
function classifyTimeWindow(timeWindow: string): 'morning' | 'afternoon' | 'all_day' {
  // Split on dash, en-dash, or em-dash
  const parts = timeWindow.split(/[–—-]/);
  const startPart = (parts[0] ?? '').trim().toUpperCase();
  const endPart = (parts[1] ?? '').trim().toUpperCase();

  // Check start time first
  if (startPart.includes('AM')) return 'morning';
  if (startPart.includes('PM')) return 'afternoon';

  // Start has no AM/PM indicator, fall back to end time
  if (endPart.includes('AM')) return 'morning';
  if (endPart.includes('PM')) return 'afternoon';

  // Neither part has AM/PM — treat as all day
  return 'all_day';
}

export function PatternCardGrid({ strategies, selectedId, onSelect }: PatternCardGridProps) {
  const { filters, sortBy, setFilter, setSortBy } = usePatternLibraryUI();

  // Apply filters
  const filteredStrategies = useMemo(() => {
    return strategies.filter((strategy) => {
      // Stage filter
      if (filters.stage && strategy.pipeline_stage !== filters.stage) {
        return false;
      }

      // Family filter
      if (filters.family && strategy.family !== filters.family) {
        return false;
      }

      // Time window filter
      if (filters.timeWindow) {
        const classification = classifyTimeWindow(strategy.time_window);
        // all_day matches both morning and afternoon filters
        if (classification !== 'all_day' && classification !== filters.timeWindow) {
          return false;
        }
      }

      return true;
    });
  }, [strategies, filters]);

  // Apply sorting
  const sortedStrategies = useMemo(() => {
    const sorted = [...filteredStrategies];

    sorted.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);

        case 'pnl': {
          const pnlA = a.performance_summary?.net_pnl ?? -Infinity;
          const pnlB = b.performance_summary?.net_pnl ?? -Infinity;
          return pnlB - pnlA; // high to low
        }

        case 'win_rate': {
          const wrA = a.performance_summary?.win_rate ?? -Infinity;
          const wrB = b.performance_summary?.win_rate ?? -Infinity;
          return wrB - wrA; // high to low
        }

        case 'trades': {
          const tA = a.performance_summary?.trade_count ?? -Infinity;
          const tB = b.performance_summary?.trade_count ?? -Infinity;
          return tB - tA; // high to low
        }

        default:
          return 0;
      }
    });

    return sorted;
  }, [filteredStrategies, sortBy]);

  return (
    <div>
      <PatternFilters
        filters={filters}
        sortBy={sortBy}
        onFilterChange={setFilter}
        onSortChange={setSortBy}
      />

      {sortedStrategies.length === 0 ? (
        <EmptyState
          icon={Filter}
          message="No strategies match the current filters."
        />
      ) : (
        <div className="space-y-3">
          {sortedStrategies.map((strategy) => (
            <PatternCard
              key={strategy.strategy_id}
              strategy={strategy}
              isSelected={selectedId === strategy.strategy_id}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
