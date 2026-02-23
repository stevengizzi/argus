/**
 * TanStack Query hook for sparkline data.
 *
 * Fetches monthly performance data and extracts trend arrays for sparklines.
 * Refreshes every 5 seconds to stay in sync with account data updates.
 */

import { useQuery } from '@tanstack/react-query';
import { getPerformance } from '../api/client';
import { useMemo } from 'react';

interface SparklineData {
  /** Cumulative equity trend (for account equity sparkline) */
  equityTrend: number[];
  /** Daily P&L values (for P&L sparkline) */
  pnlTrend: number[];
  /** Whether data is currently loading */
  isLoading: boolean;
  /** Net direction of P&L trend (positive, negative, or zero) */
  pnlDirection: 'positive' | 'negative' | 'neutral';
}

export function useSparklineData(): SparklineData {
  const { data, isLoading } = useQuery({
    queryKey: ['performance', 'month'],
    queryFn: () => getPerformance('month'),
    staleTime: 5_000, // 5 seconds
    refetchInterval: 5_000, // Refetch every 5 seconds to match account data
  });

  return useMemo(() => {
    if (!data || data.daily_pnl.length === 0) {
      return {
        equityTrend: [],
        pnlTrend: [],
        isLoading,
        pnlDirection: 'neutral' as const,
      };
    }

    // Sort daily P&L by date (oldest first)
    const sortedDailyPnl = [...data.daily_pnl].sort((a, b) =>
      a.date.localeCompare(b.date)
    );

    // Extract raw P&L values for P&L sparkline
    const pnlTrend = sortedDailyPnl.map((entry) => entry.pnl);

    // Compute cumulative equity trend
    const equityTrend = sortedDailyPnl.reduce<number[]>((acc, entry) => {
      const prevCumulative = acc.length > 0 ? acc[acc.length - 1] : 0;
      acc.push(prevCumulative + entry.pnl);
      return acc;
    }, []);

    // Determine net P&L direction
    const totalPnl = pnlTrend.reduce((sum, val) => sum + val, 0);
    const pnlDirection =
      totalPnl > 0 ? 'positive' : totalPnl < 0 ? 'negative' : 'neutral';

    return {
      equityTrend,
      pnlTrend,
      isLoading,
      pnlDirection: pnlDirection as 'positive' | 'negative' | 'neutral',
    };
  }, [data, isLoading]);
}
