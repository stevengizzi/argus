/**
 * Hook to sort and filter strategies for the Pattern Library.
 *
 * Centralizes the filtering and sorting logic so it can be shared between
 * PatternCardGrid (for display) and PatternLibraryPage (for keyboard navigation).
 */

import { useMemo } from 'react';
import { usePatternLibraryUI } from '../stores/patternLibraryUI';
import type { StrategyInfo } from '../api/types';

/**
 * Classify a time window string as 'morning' or 'afternoon'.
 */
function classifyTimeWindow(timeWindow: string): 'morning' | 'afternoon' | 'all_day' {
  const parts = timeWindow.split(/[–—-]/);
  const startPart = (parts[0] ?? '').trim().toUpperCase();
  const endPart = (parts[1] ?? '').trim().toUpperCase();

  if (startPart.includes('AM')) return 'morning';
  if (startPart.includes('PM')) return 'afternoon';
  if (endPart.includes('AM')) return 'morning';
  if (endPart.includes('PM')) return 'afternoon';

  return 'all_day';
}

export function useSortedStrategies(strategies: StrategyInfo[]): StrategyInfo[] {
  const { filters, sortBy } = usePatternLibraryUI();

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
          return pnlB - pnlA;
        }

        case 'win_rate': {
          const wrA = a.performance_summary?.win_rate ?? -Infinity;
          const wrB = b.performance_summary?.win_rate ?? -Infinity;
          return wrB - wrA;
        }

        case 'trades': {
          const tA = a.performance_summary?.trade_count ?? -Infinity;
          const tB = b.performance_summary?.trade_count ?? -Infinity;
          return tB - tA;
        }

        default:
          return 0;
      }
    });

    return sorted;
  }, [filteredStrategies, sortBy]);

  return sortedStrategies;
}
