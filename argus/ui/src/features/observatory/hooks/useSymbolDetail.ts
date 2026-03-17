/**
 * TanStack Query hook that fetches and combines data for the Observatory
 * detail panel: journey events, quality score, catalysts, and candle bars.
 *
 * Queries keyed on symbol — automatic refetch when symbol changes.
 * Queries disabled when symbol is null.
 * In debrief mode (date prop provided), polling is disabled.
 *
 * Sprint 25, Session 4b.
 */

import { useQuery } from '@tanstack/react-query';
import {
  getSymbolJourney,
  getQualityScore,
  getCatalystsBySymbol,
  fetchSymbolBars,
} from '../../../api/client';
import type { ObservatoryJourneyResponse } from '../../../api/client';
import type { BarsResponse } from '../../../api/types';
import type { QualityScoreResponse, CatalystsBySymbolResponse } from '../../../api/types';

interface UseSymbolDetailOptions {
  symbol: string | null;
  date?: string;
}

interface SymbolDetailData {
  journey: ObservatoryJourneyResponse | undefined;
  quality: QualityScoreResponse | undefined;
  catalysts: CatalystsBySymbolResponse | undefined;
  candles: BarsResponse | undefined;
  isLoading: boolean;
  error: Error | null;
}

export function useSymbolDetail({ symbol, date }: UseSymbolDetailOptions): SymbolDetailData {
  const isDebrief = date !== undefined;
  const enabled = symbol !== null && symbol !== '';

  const journeyQuery = useQuery({
    queryKey: ['observatory', 'journey', symbol, date],
    queryFn: () => getSymbolJourney(symbol!, date),
    enabled,
    staleTime: 5_000,
    refetchInterval: isDebrief ? false : 5_000,
  });

  const qualityQuery = useQuery({
    queryKey: ['observatory', 'quality', symbol],
    queryFn: () => getQualityScore(symbol!),
    enabled,
    staleTime: 30_000,
    refetchInterval: isDebrief ? false : 30_000,
  });

  const catalystQuery = useQuery({
    queryKey: ['observatory', 'catalysts', symbol],
    queryFn: () => getCatalystsBySymbol(symbol!, 5),
    enabled,
    staleTime: 60_000,
    refetchInterval: isDebrief ? false : 60_000,
  });

  const candleQuery = useQuery({
    queryKey: ['observatory', 'candles', symbol],
    queryFn: () => fetchSymbolBars(symbol!, 390),
    enabled,
    staleTime: 15_000,
    refetchInterval: isDebrief ? false : 15_000,
  });

  const isLoading =
    journeyQuery.isLoading || qualityQuery.isLoading ||
    catalystQuery.isLoading || candleQuery.isLoading;

  const error =
    journeyQuery.error ?? qualityQuery.error ??
    catalystQuery.error ?? candleQuery.error ?? null;

  return {
    journey: journeyQuery.data,
    quality: qualityQuery.data,
    catalysts: catalystQuery.data,
    candles: candleQuery.data,
    isLoading,
    error,
  };
}
