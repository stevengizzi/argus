/**
 * TanStack Query key registry.
 *
 * Audit FIX-12 finding P1-F2-M03 flagged inconsistent query-key shape across
 * ~85 `useQuery` call sites: some have a domain prefix (`['observatory', ...]`),
 * some don't (`['account']`), some use nested arrays, some flat. The inconsistency
 * makes `queryClient.invalidateQueries({ queryKey: ['briefings'] })` error-prone
 * because a sibling hook keyed differently silently misses invalidation.
 *
 * This module registers the canonical shape: `[domain, subDomain?, ...params]`,
 * always as an `as const` tuple so TypeScript preserves literal types. New
 * hooks should import from here; existing hooks are migrated opportunistically
 * during page touches — not a big-bang migration.
 *
 * Usage:
 * ```ts
 * useQuery({ queryKey: qk.account(), queryFn: fetchAccount });
 * useQuery({ queryKey: qk.catalystsBySymbol('NVDA'), queryFn: () => getCatalystsBySymbol('NVDA') });
 *
 * // Invalidate:
 * queryClient.invalidateQueries({ queryKey: qk.briefings() });   // all briefings queries
 * queryClient.invalidateQueries({ queryKey: qk.briefing(id) });  // one briefing
 * ```
 */

export const qk = {
  // Account / P&L
  account: () => ['account'] as const,

  // Positions
  positions: () => ['positions'] as const,
  position: (id: string) => ['position', id] as const,

  // Trades
  trades: (filters?: Record<string, unknown>) =>
    (filters ? ['trades', filters] : ['trades']) as const,
  tradeStats: (filters?: Record<string, unknown>) =>
    (filters ? ['trade-stats', filters] : ['trade-stats']) as const,
  symbolTrades: (symbol: string) => ['trades', 'symbol', symbol] as const,

  // Performance
  performance: (period: string) => ['performance', period] as const,
  distribution: (period: string) => ['distribution', period] as const,
  heatmap: (period: string) => ['heatmap', period] as const,
  correlation: (period: string) => ['correlation', period] as const,

  // Strategies / orchestrator
  strategies: () => ['strategies'] as const,
  strategyDecisions: (strategyId: string) => ['strategy-decisions', strategyId] as const,
  orchestratorStatus: () => ['orchestrator-status'] as const,
  orchestratorDecisions: () => ['orchestrator-decisions'] as const,

  // Watchlist / universe
  watchlist: () => ['watchlist'] as const,
  universeStatus: () => ['universe-status'] as const,

  // Catalysts
  catalysts: () => ['catalysts'] as const,
  catalystsBySymbol: (symbol: string) => ['catalysts', 'symbol', symbol] as const,
  recentCatalysts: (limit: number) => ['catalysts', 'recent', limit] as const,

  // Briefings / documents / journal
  briefings: (filters?: Record<string, unknown>) =>
    (filters ? ['briefings', filters] : ['briefings']) as const,
  briefing: (id: string | null) => ['briefing', id] as const,
  documents: () => ['documents'] as const,
  journal: () => ['journal'] as const,

  // Arena
  arenaPositions: () => ['arena', 'positions'] as const,
  arenaCandles: (symbol: string) => ['arena', 'candles', symbol] as const,

  // Observatory
  observatorySymbolDetail: (symbol: string) => ['observatory', 'symbol-detail', symbol] as const,
  observatoryMatrix: (tier: string, date: string) =>
    ['observatory', 'matrix', tier, date] as const,
  observatoryClosestMisses: (tier: string, date: string) =>
    ['observatory', 'closest-misses', tier, date] as const,

  // Experiments / counterfactual / learning
  experiments: () => ['experiments'] as const,
  experimentPromotions: () => ['experiments', 'promotions'] as const,
  shadowTrades: (filters?: Record<string, unknown>) =>
    (filters ? ['shadow-trades', filters] : ['shadow-trades']) as const,
  learningReport: () => ['learning', 'report'] as const,
  configProposals: (status?: string) =>
    (status ? ['config-proposals', status] : ['config-proposals']) as const,

  // System / health / VIX / regime / quality
  health: () => ['health'] as const,
  vix: () => ['vix', 'current'] as const,
  vixHistory: () => ['vix', 'history'] as const,
  quality: () => ['quality'] as const,
  sessionSummary: () => ['session-summary'] as const,

  // Dashboard / sparkline
  dashboardSummary: () => ['dashboard-summary'] as const,
  sparkline: (symbol: string) => ['sparkline', symbol] as const,
} as const;
