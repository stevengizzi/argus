/**
 * Trade filters state store using Zustand.
 *
 * Manages filter state for the Trades page (strategy, outcome, date range, quick filter).
 * State persists across page navigation within a session.
 * Session-level only — does not persist to localStorage.
 */

import { create } from 'zustand';

export type OutcomeFilter = 'all' | 'win' | 'loss' | 'breakeven';
export type QuickFilter = 'today' | 'week' | 'month' | 'all';

interface TradeFiltersState {
  // Filter values
  strategyId: string | undefined;
  outcome: OutcomeFilter;
  dateFrom: string | undefined;
  dateTo: string | undefined;
  quickFilter: QuickFilter;

  // Actions
  setStrategyId: (strategyId: string | undefined) => void;
  setOutcome: (outcome: OutcomeFilter) => void;
  setDateRange: (dateFrom: string | undefined, dateTo: string | undefined) => void;
  setQuickFilter: (quickFilter: QuickFilter) => void;
  clearFilters: () => void;
}

/**
 * Get today's date in ET timezone as YYYY-MM-DD.
 */
function getTodayET(): string {
  const now = new Date();
  const etFormatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  return etFormatter.format(now);
}

/**
 * Get Monday of the current week in ET timezone as YYYY-MM-DD.
 */
function getMondayOfWeekET(): string {
  const now = new Date();
  // Get current day in ET
  const etFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    weekday: 'short',
  });
  const dayName = etFormatter.format(now);

  // Calculate days since Monday (Mon=0, Sun=6)
  const daysMap: Record<string, number> = {
    Mon: 0,
    Tue: 1,
    Wed: 2,
    Thu: 3,
    Fri: 4,
    Sat: 5,
    Sun: 6,
  };
  const daysSinceMonday = daysMap[dayName] ?? 0;

  // Subtract days to get to Monday
  const monday = new Date(now);
  monday.setDate(monday.getDate() - daysSinceMonday);

  const dateFormatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  return dateFormatter.format(monday);
}

/**
 * Get the first day of the current month in ET timezone as YYYY-MM-DD.
 */
function getFirstOfMonthET(): string {
  const now = new Date();
  const etFormatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: '2-digit',
  });
  const yearMonth = etFormatter.format(now); // e.g., "2026-03"
  return `${yearMonth}-01`;
}

/**
 * Compute date range for a quick filter.
 */
export function computeDateRangeForQuickFilter(
  quickFilter: QuickFilter
): { dateFrom: string | undefined; dateTo: string | undefined } {
  switch (quickFilter) {
    case 'today': {
      const today = getTodayET();
      return { dateFrom: today, dateTo: today };
    }
    case 'week': {
      return { dateFrom: getMondayOfWeekET(), dateTo: getTodayET() };
    }
    case 'month': {
      return { dateFrom: getFirstOfMonthET(), dateTo: getTodayET() };
    }
    case 'all':
    default:
      return { dateFrom: undefined, dateTo: undefined };
  }
}

export const useTradeFiltersStore = create<TradeFiltersState>((set) => ({
  // Initial state
  strategyId: undefined,
  outcome: 'all',
  dateFrom: undefined,
  dateTo: undefined,
  quickFilter: 'all',

  // Actions
  setStrategyId: (strategyId) => set({ strategyId }),
  setOutcome: (outcome) => set({ outcome }),
  setDateRange: (dateFrom, dateTo) =>
    set({ dateFrom, dateTo, quickFilter: 'all' }), // Clear quick filter when manually setting dates
  setQuickFilter: (quickFilter) => {
    const { dateFrom, dateTo } = computeDateRangeForQuickFilter(quickFilter);
    set({ quickFilter, dateFrom, dateTo });
  },
  clearFilters: () =>
    set({
      strategyId: undefined,
      outcome: 'all',
      dateFrom: undefined,
      dateTo: undefined,
      quickFilter: 'all',
    }),
}));
