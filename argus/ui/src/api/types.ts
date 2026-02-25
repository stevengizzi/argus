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
}

export interface TradesResponse {
  trades: Trade[];
  total_count: number;
  limit: number;
  offset: number;
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
}

export interface StrategiesResponse {
  strategies: StrategyInfo[];
  count: number;
  timestamp: string;
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
}

export interface WatchlistResponse {
  symbols: WatchlistItem[];
  count: number;
  timestamp: string;
}

// Orchestrator
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
}
