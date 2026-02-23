/**
 * TanStack Query hooks for Argus API data fetching.
 */

export { useAccount } from './useAccount';
export {
  usePauseStrategy,
  useResumeStrategy,
  useClosePosition,
  useEmergencyFlatten,
  useEmergencyPauseAll,
} from './useControls';
export { useHealth } from './useHealth';
export { useLiveEquity, type LiveEquityData } from './useLiveEquity';
export { usePerformance } from './usePerformance';
export { usePositions } from './usePositions';
export { useSparklineData } from './useSparklineData';
export { useStrategies } from './useStrategies';
export { useTrades, type UseTradesParams } from './useTrades';
export { useTradeFilters, type TradeFilterValues, type OutcomeFilter } from './useTradeFilters';
