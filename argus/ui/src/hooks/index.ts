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
export { useOrchestratorDecisions } from './useOrchestratorDecisions';
export {
  useRebalanceMutation,
  useThrottleOverrideMutation,
} from './useOrchestratorMutations';
export { useOrchestratorStatus } from './useOrchestratorStatus';
export { usePerformance } from './usePerformance';
export { usePositions } from './usePositions';
export { useSparklineData } from './useSparklineData';
export { useStrategies } from './useStrategies';
export { useStrategySpec } from './useStrategySpec';
export { useSessionSummary } from './useSessionSummary';
export { useSymbolBars } from './useSymbolBars';
export { useSymbolTrades } from './useSymbolTrades';
export { useTrades, type UseTradesParams } from './useTrades';
export { useTradeFilters, type TradeFilterValues, type OutcomeFilter } from './useTradeFilters';

// Debrief hooks
export {
  useBriefings,
  useBriefing,
  useCreateBriefing,
  useUpdateBriefing,
  useDeleteBriefing,
} from './useBriefings';
export {
  useDocuments,
  useDocument,
  useCreateDocument,
  useUpdateDocument,
  useDeleteDocument,
  useDocumentTags,
} from './useDocuments';
export {
  useJournalEntries,
  useJournalEntry,
  useCreateJournalEntry,
  useUpdateJournalEntry,
  useDeleteJournalEntry,
  useJournalTags,
} from './useJournal';
export { useDebriefSearch, type SearchScope } from './useDebriefSearch';
