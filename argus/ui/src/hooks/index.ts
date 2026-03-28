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

// Performance analytics hooks (Sprint 21d)
export { useHeatmapData } from './useHeatmapData';
export { useDistribution } from './useDistribution';
export { useCorrelation } from './useCorrelation';
export { useTradeReplay } from './useTradeReplay';
export { useGoals } from './useGoals';

// AI hooks (Sprint 22 Session 6)
export {
  useAIStatus,
  useAIInsight,
  useConversations,
  useConversation,
  type ConversationFilters,
} from './useAI';

// Universe Manager hooks (Sprint 23)
export { useUniverseStatus } from './useUniverseStatus';

// Pipeline status hook (Sprint 23.9)
export { usePipelineStatus } from './usePipelineStatus';

// VIX Regime hooks (Sprint 27.9)
export { useVixData } from './useVixData';

// Learning Loop hooks (Sprint 28)
export {
  useLearningReport,
  useLearningReports,
  useTriggerAnalysis,
} from './useLearningReport';
export {
  useConfigProposals,
  useApproveProposal,
  useDismissProposal,
  useRevertProposal,
} from './useConfigProposals';

// Intelligence hooks (Sprint 23.5)
export {
  useCatalystsBySymbol,
  useRecentCatalysts,
  type CatalystItem,
  type CatalystsResponse,
} from './useCatalysts';
export {
  useIntelligenceBriefing,
  useIntelligenceBriefingHistory,
  useGenerateIntelligenceBriefing,
  type IntelligenceBrief,
} from './useIntelligenceBriefings';
