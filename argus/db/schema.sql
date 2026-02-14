-- Argus Trading System Database Schema
-- SQLite with WAL mode for concurrent access

-- Enable WAL mode and foreign keys
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Trades Table
-- ---------------------------------------------------------------------------
-- Every completed trade is logged here with full metadata
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,                    -- ULID
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'us_stocks',
    side TEXT NOT NULL,                     -- 'buy' or 'sell'
    entry_price REAL NOT NULL,
    entry_time TEXT NOT NULL,               -- ISO-8601 datetime
    exit_price REAL NOT NULL,
    exit_time TEXT NOT NULL,                -- ISO-8601 datetime
    shares INTEGER NOT NULL,
    stop_price REAL NOT NULL,
    target_prices TEXT,                     -- JSON array
    exit_reason TEXT NOT NULL,
    gross_pnl REAL NOT NULL,
    commission REAL NOT NULL DEFAULT 0,
    net_pnl REAL NOT NULL,
    r_multiple REAL NOT NULL DEFAULT 0,
    hold_duration_seconds INTEGER NOT NULL DEFAULT 0,
    outcome TEXT NOT NULL,                  -- 'win', 'loss', 'breakeven'
    rationale TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time);
CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time);
CREATE INDEX IF NOT EXISTS idx_trades_outcome ON trades(outcome);

-- ---------------------------------------------------------------------------
-- Orders Table
-- ---------------------------------------------------------------------------
-- All orders submitted to brokers
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,                    -- ULID
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'us_stocks',
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    limit_price REAL,
    stop_price REAL,
    time_in_force TEXT NOT NULL DEFAULT 'day',
    status TEXT NOT NULL,
    broker_order_id TEXT,
    filled_quantity INTEGER NOT NULL DEFAULT 0,
    filled_avg_price REAL NOT NULL DEFAULT 0,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_orders_strategy ON orders(strategy_id);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);

-- ---------------------------------------------------------------------------
-- Positions Table
-- ---------------------------------------------------------------------------
-- Current and historical positions
CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,                    -- ULID
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'us_stocks',
    side TEXT NOT NULL,
    status TEXT NOT NULL,                   -- 'open' or 'closed'
    entry_price REAL NOT NULL,
    entry_time TEXT NOT NULL,
    shares INTEGER NOT NULL,
    stop_price REAL NOT NULL,
    target_prices TEXT,                     -- JSON array
    current_price REAL NOT NULL DEFAULT 0,
    unrealized_pnl REAL NOT NULL DEFAULT 0,
    exit_price REAL,
    exit_time TEXT,
    exit_reason TEXT,
    realized_pnl REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_positions_strategy ON positions(strategy_id);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);

-- ---------------------------------------------------------------------------
-- Daily Summaries Table
-- ---------------------------------------------------------------------------
-- Aggregated daily performance metrics
CREATE TABLE IF NOT EXISTS daily_summaries (
    id TEXT PRIMARY KEY,                    -- ULID
    date TEXT NOT NULL,                     -- YYYY-MM-DD
    strategy_id TEXT,                       -- NULL for account-wide
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    win_rate REAL NOT NULL DEFAULT 0,
    gross_pnl REAL NOT NULL DEFAULT 0,
    commissions REAL NOT NULL DEFAULT 0,
    net_pnl REAL NOT NULL DEFAULT 0,
    avg_winner REAL NOT NULL DEFAULT 0,
    avg_loser REAL NOT NULL DEFAULT 0,
    largest_winner REAL NOT NULL DEFAULT 0,
    largest_loser REAL NOT NULL DEFAULT 0,
    avg_r_multiple REAL NOT NULL DEFAULT 0,
    profit_factor REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(date, strategy_id)
);

CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON daily_summaries(date);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_strategy ON daily_summaries(strategy_id);

-- ---------------------------------------------------------------------------
-- Risk Events Table
-- ---------------------------------------------------------------------------
-- Circuit breaker triggers and risk limit violations
CREATE TABLE IF NOT EXISTS risk_events (
    id TEXT PRIMARY KEY,                    -- ULID
    event_type TEXT NOT NULL,               -- 'circuit_breaker', 'rejection', etc.
    level TEXT NOT NULL,                    -- 'strategy', 'cross_strategy', 'account'
    strategy_id TEXT,                       -- NULL if account-level
    reason TEXT NOT NULL,
    details TEXT,                           -- JSON with additional context
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_risk_events_type ON risk_events(event_type);
CREATE INDEX IF NOT EXISTS idx_risk_events_created ON risk_events(created_at);

-- ---------------------------------------------------------------------------
-- System Events Table
-- ---------------------------------------------------------------------------
-- System health, heartbeats, and status changes
CREATE TABLE IF NOT EXISTS system_events (
    id TEXT PRIMARY KEY,                    -- ULID
    event_type TEXT NOT NULL,
    status TEXT,
    details TEXT,                           -- JSON
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type);
CREATE INDEX IF NOT EXISTS idx_system_events_created ON system_events(created_at);
