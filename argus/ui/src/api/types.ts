/**
 * TypeScript interfaces for Argus Command Center API responses.
 */

// Auth
export interface LoginRequest {
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  timestamp: string;
}

// Account
export interface AccountInfo {
  equity: number;
  cash: number;
  buying_power: number;
  portfolio_value: number;
  currency: string;
  timestamp: string;
}

// Positions
export interface Position {
  symbol: string;
  strategy_id: string;
  entry_price: number;
  entry_time: string;
  shares_total: number;
  shares_remaining: number;
  stop_price: number;
  original_stop_price: number;
  t1_price: number;
  t1_filled: boolean;
  t2_price: number;
  high_watermark: number;
  realized_pnl: number;
  current_price?: number;
  unrealized_pnl?: number;
  pnl_percent?: number;
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
  side: 'buy' | 'sell';
  entry_price: number;
  entry_time: string;
  exit_price: number;
  exit_time: string;
  shares: number;
  stop_price: number;
  target_prices: number[];
  exit_reason: string;
  gross_pnl: number;
  commission: number;
  net_pnl: number;
  r_multiple: number;
  hold_duration_seconds: number;
  outcome: 'win' | 'loss' | 'breakeven';
  rationale: string;
}

export interface TradesResponse {
  trades: Trade[];
  count: number;
  total_count: number;
  limit: number;
  offset: number;
  timestamp: string;
}

// Performance
export interface PerformanceMetrics {
  total_trades: number;
  wins: number;
  losses: number;
  breakeven: number;
  win_rate: number;
  profit_factor: number;
  net_pnl: number;
  gross_pnl: number;
  total_commissions: number;
  avg_r_multiple: number;
  sharpe_ratio: number | null;
  max_drawdown_pct: number;
  avg_hold_seconds: number;
  largest_win: number;
  largest_loss: number;
  consecutive_wins_max: number;
  consecutive_losses_max: number;
  timestamp: string;
}

export interface DailyPnl {
  date: string;
  pnl: number;
  trades_count: number;
}

export interface DailyPnlResponse {
  daily_pnl: DailyPnl[];
  count: number;
  timestamp: string;
}

// Health
export interface ComponentHealth {
  name: string;
  status: 'starting' | 'healthy' | 'degraded' | 'unhealthy' | 'stopped';
  message: string;
  last_updated: string;
  details?: Record<string, unknown>;
}

export interface HealthResponse {
  overall_status: string;
  components: ComponentHealth[];
  uptime_seconds: number;
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
  config: Record<string, unknown>;
  timestamp: string;
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
