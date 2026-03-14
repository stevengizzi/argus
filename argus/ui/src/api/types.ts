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
