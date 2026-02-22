/**
 * Hook to get current performance period from URL.
 *
 * Extracted from PeriodSelector to enable fast refresh.
 */

import { useSearchParams } from 'react-router-dom';
import type { PerformancePeriod } from '../api/types';

export function useSelectedPeriod(): PerformancePeriod {
  const [searchParams] = useSearchParams();
  return (searchParams.get('period') as PerformancePeriod) || 'month';
}
