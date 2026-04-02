/**
 * TypeScript interfaces for Argus Command Center API responses.
 *
 * These types match the Python Pydantic models in argus/api/routes/*.py exactly.
 */

// Auth
export interface LoginRequest {
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
}

// Account
export interface AccountResponse {
  equity: number;
  cash: number;
  buying_power: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  open_positions_count: number;
  daily_trades_count: number;
  market_status: 'pre_market' | 'open' | 'closed' | 'after_hours';
  broker_source: string;
  data_source: string;
  timestamp: string;
}

// Positions
export interface Position {
  position_id: string;
  strategy_id: string;
  symbol: string;
  side: string;
  entry_price: number;
  entry_time: string;
  shares_total: number;
  shares_remaining: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  stop_price: number;
  t1_price: number;
  t2_price: number;
  t1_filled: boolean;
  hold_duration_seconds: number;
  r_multiple_current: number;
}

export interface PositionsResponse {
  positions: Position[];
  count: number;
  timestamp: string;
}

// Trades
export interface Trade {
  id: string;
  strategy_id: string;
  symbol: string;
  side: string;
  entry_price: number;
  entry_time: string;
  exit_price: number | null;
  exit_time: string | null;
  shares: number;
  pnl_dollars: number | null;
  pnl_r_multiple: number | null;
  exit_reason: string | null;
  hold_duration_seconds: number | null;
  commission: number;
  market_regime: string | null;
  stop_price: number | null;
  target_prices: number[] | null;
  quality_grade: string | null;
  quality_score: number | null;
}

export interface TradesResponse {
  trades: Trade[];
  total_count: number;
  limit: number;
  offset: number;
  timestamp: string;
}

export interface TradesBatchResponse {
  trades: Trade[];
  count: number;
  timestamp: string;
}

// Shadow (counterfactual) trades
export interface ShadowTrade {
  position_id: string;
  symbol: string;
  strategy_id: string;
  variant_id: string | null;
  entry_price: number;
  stop_price: number;
  target_price: number;
  time_stop_seconds: number | null;
  rejection_stage: string;
  rejection_reason: string;
  quality_score: number | null;
  quality_grade: string | null;
  opened_at: string;
  closed_at: string | null;
  exit_price: number | null;
  exit_reason: string | null;
  theoretical_pnl: number | null;
  theoretical_r_multiple: number | null;
  duration_seconds: number | null;
  max_adverse_excursion: number | null;
  max_favorable_excursion: number | null;
  bars_monitored: number;
}

export interface ShadowTradesResponse {
  positions: ShadowTrade[];
  total_count: number;
  limit: number;
  offset: number;
  timestamp: string;
}

// Trade Stats (server-side aggregation)
export interface TradeStatsResponse {
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  net_pnl: number;
  avg_r: number | null;
  timestamp: string;
}

// Performance
export interface MetricsData {
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  net_pnl: number;
  gross_pnl: number;
  total_commissions: number;
  avg_r_multiple: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  avg_hold_seconds: number;
  largest_win: number;
  largest_loss: number;
  consecutive_wins_max: number;
  consecutive_losses_max: number;
}

export interface DailyPnlEntry {
  date: string;
  pnl: number;
  trades: number;
}

export interface StrategyMetrics {
  total_trades: number;
  win_rate: number;
  net_pnl: number;
  profit_factor: number;
}

export interface PerformanceResponse {
  period: string;
  date_from: string;
  date_to: string;
  metrics: MetricsData;
  daily_pnl: DailyPnlEntry[];
  by_strategy: Record<string, StrategyMetrics>;
  timestamp: string;
}

// Health
export interface ComponentStatus {
  status: string;
  details: string;
}

export interface HealthResponse {
  status: string;
  uptime_seconds: number;
  components: Record<string, ComponentStatus>;
  last_heartbeat: string | null;
  last_trade: string | null;
  last_data_received: string | null;
  paper_mode: boolean;
  timestamp: string;
}

// Strategies
export interface PerformanceSummary {
  trade_count: number;
  win_rate: number;
  net_pnl: number;
  avg_r: number;
  profit_factor: number;
}

export interface BacktestSummary {
  status: string;
  wfe_pnl: number | null;
  oos_sharpe: number | null;
  total_trades: number | null;
  data_months: number | null;
  last_run: string | null;
}

export interface StrategyInfo {
  strategy_id: string;
  name: string;
  version: string;
  is_active: boolean;
  pipeline_stage: string;
  allocated_capital: number;
  daily_pnl: number;
  trade_count_today: number;
  open_positions: number;
  config_summary: Record<string, unknown>;
  time_window: string;
  family: string;
  description_short: string;
  performance_summary: PerformanceSummary | null;
  backtest_summary: BacktestSummary | null;
}

export interface StrategiesResponse {
  strategies: StrategyInfo[];
  count: number;
  timestamp: string;
}

// Strategy Spec (Pattern Library)
export interface StrategyDocument {
  doc_id: string;
  title: string;
  filename: string;
  word_count: number;
  reading_time_min: number;
  last_modified: string;
  content: string;
}

export interface StrategySpecResponse {
  strategy_id: string;
  documents: StrategyDocument[];
}

// Market Data
export interface BarData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BarsResponse {
  symbol: string;
  timeframe: string;
  bars: BarData[];
  count: number;
}

// WebSocket
export interface WebSocketMessage {
  type: string;
  data: unknown;
  sequence: number;
  timestamp: string;
}

// Period type for performance endpoint
export type PerformancePeriod = 'today' | 'week' | 'month' | 'all';

// Session Summary
export interface TradeHighlight {
  symbol: string;
  r_multiple: number;
  pnl_dollars: number;
  strategy_id: string;
}

export interface SessionSummaryResponse {
  date: string;
  trade_count: number;
  wins: number;
  losses: number;
  breakeven: number;
  net_pnl: number;
  win_rate: number;
  best_trade: TradeHighlight | null;
  worst_trade: TradeHighlight | null;
  fill_rate: number;
  regime: string | null;
  active_strategies: string[];
  timestamp: string;
}

// Watchlist
export type VwapState = 'watching' | 'above_vwap' | 'below_vwap' | 'entered';

export interface SparklinePoint {
  timestamp: string;
  price: number;
}

export interface WatchlistItem {
  symbol: string;
  current_price: number;
  gap_pct: number;
  strategies: string[];  // ["orb", "scalp", "vwap_reclaim"]
  vwap_state: VwapState;
  sparkline: SparklinePoint[];
  vwap_distance_pct: number | null;  // (current_price - vwap) / vwap, signed. Null if VWAP not tracked.
  scan_source: string;  // "fmp" | "fmp_fallback" | "static" | ""
  selection_reason: string;  // "gap_up_3.2%" | "gap_down_1.8%" | "high_volume" | ""
}

export interface WatchlistResponse {
  symbols: WatchlistItem[];
  count: number;
  timestamp: string;
}

// Orchestrator
export interface OperatingWindow {
  earliest_entry: string;
  latest_entry: string;
  force_close: string;
}

export interface AllocationInfo {
  strategy_id: string;
  allocation_pct: number;
  allocation_dollars: number;
  throttle_action: string;
  eligible: boolean;
  reason: string;
  // Deployment state (Sprint 18.75)
  deployed_capital: number;
  deployed_pct: number;
  is_throttled: boolean;
  // Extended fields (Sprint 21b)
  operating_window: OperatingWindow | null;
  consecutive_losses: number;
  rolling_sharpe: number | null;
  drawdown_pct: number;
  is_active: boolean;
  health_status: string;
  trade_count_today: number;
  daily_pnl: number;
  open_position_count: number;
  override_active: boolean;
  override_until: string | null;
}

export interface OrchestratorStatusResponse {
  regime: string;
  regime_indicators: Record<string, number>;
  regime_updated_at: string | null;
  allocations: AllocationInfo[];
  cash_reserve_pct: number;
  total_deployed_pct: number;
  next_regime_check: string | null;
  // Deployment state (Sprint 18.75)
  total_deployed_capital: number;
  total_equity: number;
  timestamp: string;
  // Session state (Sprint 21b)
  session_phase: string;
  pre_market_complete: boolean;
  pre_market_completed_at: string | null;
}

export interface DecisionInfo {
  id: string;
  date: string;
  decision_type: string;
  strategy_id: string | null;
  details: Record<string, unknown> | null;
  rationale: string | null;
  created_at: string;
}

export interface DecisionsResponse {
  decisions: DecisionInfo[];
  total: number;
  limit: number;
  offset: number;
  timestamp: string;
}

export interface ThrottleOverrideRequest {
  duration_minutes: number;
  reason: string;
}

// Debrief — Briefings
export interface Briefing {
  id: string;
  date: string;
  briefing_type: 'pre_market' | 'eod';
  status: 'draft' | 'final' | 'ai_generated';
  title: string;
  content: string;
  metadata: Record<string, unknown> | null;
  author: string;
  created_at: string;
  updated_at: string;
  word_count: number;
  reading_time_min: number;
}

export interface BriefingsListResponse {
  briefings: Briefing[];
  total: number;
}

// Debrief — Research Documents
export interface ResearchDocument {
  id: string;
  category: 'research' | 'strategy' | 'backtest' | 'ai_report';
  title: string;
  content: string;
  author: string;
  tags: string[];
  word_count: number;
  reading_time_min: number;
  source: 'filesystem' | 'database';
  is_editable: boolean;
  created_at: string | null;
  updated_at: string | null;
  last_modified: string | null; // Filesystem docs use this for mtime
}

export interface DocumentsListResponse {
  documents: ResearchDocument[];
  total: number;
}

export interface DocumentTagsResponse {
  tags: string[];
}

// Debrief — Journal
export type JournalEntryType = 'observation' | 'trade_annotation' | 'pattern_note' | 'system_note';

export interface JournalEntry {
  id: string;
  entry_type: JournalEntryType;
  title: string;
  content: string;
  author: string;
  linked_strategy_id: string | null;
  linked_trade_ids: string[];
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface JournalEntriesListResponse {
  entries: JournalEntry[];
  total: number;
}

export interface JournalTagsResponse {
  tags: string[];
}

// Debrief — Search
export interface DebriefSearchResponse {
  briefings: Briefing[];
  journal: JournalEntry[];
  documents: ResearchDocument[];
}

// Performance — Heatmap
export interface HeatmapCell {
  hour: number;          // 9-15 (ET)
  day_of_week: number;   // 0=Mon, 4=Fri
  trade_count: number;
  avg_r_multiple: number;
  net_pnl: number;
}

export interface HeatmapResponse {
  cells: HeatmapCell[];
  period: string;
  timestamp: string;
}

// Performance — Distribution
export interface DistributionBin {
  range_min: number;    // e.g., -1.0
  range_max: number;    // e.g., -0.75
  count: number;
  avg_pnl: number;
}

export interface DistributionResponse {
  bins: DistributionBin[];
  total_trades: number;
  mean_r: number;
  median_r: number;
  period: string;
  timestamp: string;
}

// Performance — Correlation
export interface CorrelationResponse {
  strategy_ids: string[];
  matrix: number[][];   // NxN correlation matrix
  period: string;
  data_days: number;
  message: string | null;
  timestamp: string;
}

// Trade Replay
export interface ReplayBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TradeReplayResponse {
  trade: Trade;
  bars: ReplayBar[];
  entry_bar_index: number;
  exit_bar_index: number | null;
  vwap: number[] | null;
  timestamp: string;
}

// Config — Goals
export interface GoalsConfig {
  monthly_target_usd: number;
  timestamp: string;
}

// Dashboard Summary (Sprint 21d)
export interface AccountSummaryData {
  equity: number;
  cash: number;
  buying_power: number;
  daily_pnl: number;
  daily_pnl_pct: number;
}

export interface BestTradeData {
  symbol: string;
  pnl: number;
}

export interface TodayStatsData {
  trade_count: number;
  win_rate: number | null;
  avg_r: number | null;
  best_trade: BestTradeData | null;
}

export interface GoalsData {
  monthly_target_usd: number;
  current_month_pnl: number;
  trading_days_elapsed: number;
  trading_days_remaining: number;
  avg_daily_pnl: number;
  needed_daily_pnl: number;
  pace_status: 'ahead' | 'on_pace' | 'behind';
}

export interface MarketData {
  status: 'pre_market' | 'open' | 'closed' | 'after_hours';
  time_et: string;
  is_paper: boolean;
}

export interface RegimeData {
  classification: string;
  description: string;
  updated_at: string | null;
}

export interface StrategyDeploymentInfo {
  strategy_id: string;
  abbreviation: string;
  deployed_capital: number;
  position_count: number;
  aggregate_pnl: number;
}

export interface DeploymentData {
  strategies: StrategyDeploymentInfo[];
  available_capital: number;
  total_equity: number;
}

export interface OrchestratorSummaryData {
  active_strategy_count: number;
  total_strategy_count: number;
  deployed_amount: number;
  deployed_pct: number;
  risk_used_pct: number;
  regime: string;
}

export interface DashboardSummaryResponse {
  account: AccountSummaryData;
  today_stats: TodayStatsData;
  goals: GoalsData;
  market: MarketData;
  regime: RegimeData;
  deployment: DeploymentData;
  orchestrator: OrchestratorSummaryData;
  timestamp: string;
}

// AI — Insight (Sprint 22 Session 6)
export interface AIInsightResponse {
  insight: string | null;
  generated_at: string;
  cached: boolean;
  message: string | null;
}

// AI — Status
export interface AIStatusResponse {
  enabled: boolean;
  model: string | null;
  usage: {
    today?: Record<string, unknown>;
    this_month?: Record<string, unknown>;
    per_day_average?: number;
  } | null;
}

// AI — Conversations
export interface ConversationSummary {
  id: string;
  date: string;
  tag: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationsListResponse {
  conversations: ConversationSummary[];
  total: number;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  tool_use_data: Array<{
    id: string;
    name: string;
    input: Record<string, unknown>;
  }> | null;
  page_context: Record<string, unknown> | null;
  is_complete: boolean;
  created_at: string;
}

export interface ConversationDetailResponse {
  conversation: ConversationSummary;
  messages: ConversationMessage[];
}

// AI — Conversation tag types for color coding
export type ConversationTag = 'session' | 'research' | 'debrief' | 'pre-market' | 'general';

// Quality Engine (Sprint 24)
export interface QualityComponents {
  ps: number;  // pattern_strength
  cq: number;  // catalyst_quality
  vp: number;  // volume_profile
  hm: number;  // historical_match
  ra: number;  // regime_alignment
}

export interface QualityScoreResponse {
  symbol: string;
  strategy_id: string;
  score: number;
  grade: string;
  risk_tier: string;
  components: QualityComponents;
  scored_at: string;
  outcome_realized_pnl: number | null;
  outcome_r_multiple: number | null;
}

export interface QualityHistoryResponse {
  items: QualityScoreResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface GradeDistributionResponse {
  grades: Record<string, number>;
  total: number;
  filtered: number;
}

// Universe Manager (Sprint 23)
export interface UniverseStatusResponse {
  enabled: boolean;
  total_symbols: number | null;
  viable_count: number | null;
  per_strategy_counts: Record<string, number> | null;
  last_refresh: string | null;
  reference_data_age_minutes: number | null;
}

// Catalysts (Intelligence pipeline)
export interface CatalystItem {
  headline: string;
  symbol: string;
  source: string;
  source_url: string | null;
  filing_type: string | null;
  published_at: string;
  category: string;
  quality_score: number;
  summary: string;
  trading_relevance: string;
  classified_by: string;
  classified_at: string;
}

export interface CatalystsBySymbolResponse {
  catalysts: CatalystItem[];
  count: number;
  symbol: string;
}

// Observatory (Sprint 25)
export interface ObservatoryConditionDetail {
  name: string;
  passed: boolean;
  actual_value: string | number | boolean | null;
  required_value: string | number | boolean | null;
}

export interface ObservatoryClosestMissEntry {
  symbol: string;
  strategy: string;
  conditions_passed: number;
  conditions_total: number;
  conditions_detail: ObservatoryConditionDetail[];
  timestamp: string | null;
}

export interface ObservatoryClosestMissesResponse {
  tier: string;
  items: ObservatoryClosestMissEntry[];
  count: number;
  timestamp: string;
}

// Observatory Session Summary (Sprint 25 S9)
export interface ObservatoryBlockerEntry {
  condition_name: string;
  rejection_count: number;
  percentage: number;
}

export interface ObservatoryClosestMissSummary {
  symbol: string;
  strategy: string;
  conditions_passed: number;
  conditions_total: number;
}

export interface RegimeVectorSummary {
  computed_at: string;
  trend_score: number;
  trend_conviction: number;
  volatility_level: number;
  volatility_direction: number;
  universe_breadth_score: number | null;
  breadth_thrust: boolean | null;
  average_correlation: number | null;
  correlation_regime: 'dispersed' | 'normal' | 'concentrated' | null;
  sector_rotation_phase: 'risk_on' | 'risk_off' | 'mixed' | 'transitioning' | null;
  leading_sectors: string[];
  lagging_sectors: string[];
  opening_drive_strength: number | null;
  first_30min_range_ratio: number | null;
  vwap_slope: number | null;
  direction_change_count: number | null;
  intraday_character: 'trending' | 'choppy' | 'reversal' | 'breakout' | null;
  primary_regime: string;
  regime_confidence: number;
}

export interface ObservatorySessionSummaryResponse {
  total_evaluations: number;
  total_signals: number;
  total_trades: number;
  symbols_evaluated: number;
  top_blockers: ObservatoryBlockerEntry[];
  closest_miss: ObservatoryClosestMissSummary | null;
  regime_vector_summary?: RegimeVectorSummary | null;
  date: string;
  timestamp: string;
}

// Strategy Decisions (Sprint 24.5)
export interface EvaluationEvent {
  timestamp: string;
  symbol: string;
  strategy_id: string;
  event_type: string;
  result: 'PASS' | 'FAIL' | 'INFO';
  reason: string;
  metadata: Record<string, unknown>;
}

// VIX Regime (Sprint 27.9)
export interface VixRegimeData {
  vol_regime_phase: string | null;
  vol_regime_momentum: string | null;
  term_structure_regime: string | null;
  vrp_tier: string | null;
}

export interface VixCurrentResponse {
  status: 'ok' | 'stale' | 'unavailable';
  message?: string;
  data_date?: string;
  vix_close?: number;
  vol_of_vol_ratio?: number;
  vix_percentile?: number;
  term_structure_proxy?: number;
  realized_vol_20d?: number;
  variance_risk_premium?: number;
  regime?: VixRegimeData;
  is_stale?: boolean;
  last_updated?: string;
  timestamp: string;
}

// Experiments (Sprint 32 / 32.5)
export interface ExperimentVariant {
  variant_id: string;
  pattern_name: string;
  detection_params: Record<string, unknown>;
  exit_overrides: Record<string, unknown> | null;
  config_fingerprint: string;
  mode: 'live' | 'shadow';
  status: string | null;
  trade_count: number;
  shadow_trade_count: number;
  win_rate: number | null;
  expectancy: number | null;
  sharpe: number | null;
}

export interface ExperimentVariantsResponse {
  variants: ExperimentVariant[];
  count: number;
  timestamp: string;
}

export interface PromotionEvent {
  event_id: string;
  variant_id: string;
  pattern_name: string | null;
  event_type: string;
  from_mode: string;
  to_mode: string;
  timestamp: string;
  trigger_reason: string;
  metrics_snapshot: string | null;
  shadow_trades: number | null;
  shadow_expectancy: number | null;
}

export interface PromotionEventsResponse {
  events: PromotionEvent[];
  total_count: number;
  limit: number;
  offset: number;
  timestamp: string;
}

// Arena (Sprint 32.75)

export interface ArenaPosition {
  symbol: string;
  strategy_id: string;
  side: string;
  shares: number;
  entry_price: number;
  current_price: number;
  stop_price: number;
  target_prices: number[];
  trailing_stop_price: number | null;
  unrealized_pnl: number;
  r_multiple: number;
  hold_duration_seconds: number;
  quality_grade: string;
  entry_time: string;
}

export interface ArenaStats {
  position_count: number;
  total_pnl: number;
  net_r: number;
}

export interface ArenaPositionsResponse {
  positions: ArenaPosition[];
  stats: ArenaStats;
  timestamp: string;
}

export interface ArenaCandleBar {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ArenaCandlesResponse {
  symbol: string;
  candles: ArenaCandleBar[];
}

