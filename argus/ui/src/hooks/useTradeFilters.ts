/**
 * Hook to read trade filter values from URL search params.
 *
 * Extracted from TradeFilters to enable fast refresh.
 */

import { useSearchParams } from 'react-router-dom';

export type OutcomeFilter = 'all' | 'win' | 'loss' | 'breakeven';

export interface TradeFilterValues {
  strategy_id: string | undefined;
  outcome: OutcomeFilter;
  date_from: string | undefined;
  date_to: string | undefined;
}

export function useTradeFilters(): TradeFilterValues {
  const [searchParams] = useSearchParams();

  return {
    strategy_id: searchParams.get('strategy') || undefined,
    outcome: (searchParams.get('outcome') as OutcomeFilter) || 'all',
    date_from: searchParams.get('from') || undefined,
    date_to: searchParams.get('to') || undefined,
  };
}
