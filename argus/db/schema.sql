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
    quality_grade TEXT,              -- e.g., 'B+', 'A-', '' for legacy
    quality_score REAL,              -- 0-100, NULL for legacy trades
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

-- ---------------------------------------------------------------------------
-- Strategy Daily Performance Table
-- ---------------------------------------------------------------------------
-- Per-strategy daily metrics (from Architecture doc Section 3.8)
CREATE TABLE IF NOT EXISTS strategy_daily_performance (
    date TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    trades_taken INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    gross_pnl REAL DEFAULT 0,
    net_pnl REAL DEFAULT 0,
    largest_win REAL DEFAULT 0,
    largest_loss REAL DEFAULT 0,
    avg_r_multiple REAL,
    allocated_capital REAL,
    market_regime TEXT,
    circuit_breaker_triggered INTEGER DEFAULT 0,
    PRIMARY KEY (date, strategy_id)
);

CREATE INDEX IF NOT EXISTS idx_strategy_daily_perf_date ON strategy_daily_performance(date);
CREATE INDEX IF NOT EXISTS idx_strategy_daily_perf_strategy ON strategy_daily_performance(strategy_id);

-- ---------------------------------------------------------------------------
-- Account Daily Snapshot Table
-- ---------------------------------------------------------------------------
-- Account-wide daily snapshot (from Architecture doc Section 3.8)
CREATE TABLE IF NOT EXISTS account_daily_snapshot (
    date TEXT PRIMARY KEY,
    total_equity REAL NOT NULL,
    cash_balance REAL NOT NULL,
    deployed_capital REAL NOT NULL,
    total_pnl REAL NOT NULL,
    active_strategies INTEGER,
    total_trades INTEGER,
    market_regime TEXT,
    base_capital REAL,
    growth_pool REAL
);

CREATE INDEX IF NOT EXISTS idx_account_daily_date ON account_daily_snapshot(date);

-- ---------------------------------------------------------------------------
-- Orchestrator Decisions Table
-- ---------------------------------------------------------------------------
-- Logged orchestrator decisions (from Architecture doc Section 3.8)
CREATE TABLE IF NOT EXISTS orchestrator_decisions (
    id TEXT PRIMARY KEY,                    -- ULID
    date TEXT NOT NULL,
    decision_type TEXT NOT NULL,            -- 'allocation', 'activation', 'suspension', 'throttle'
    strategy_id TEXT,
    details TEXT,                           -- JSON
    rationale TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_orchestrator_date ON orchestrator_decisions(date);
CREATE INDEX IF NOT EXISTS idx_orchestrator_type ON orchestrator_decisions(decision_type);

-- ---------------------------------------------------------------------------
-- Approval Log Table
-- ---------------------------------------------------------------------------
-- Approval workflow log (from Architecture doc Section 3.8)
CREATE TABLE IF NOT EXISTS approval_log (
    id TEXT PRIMARY KEY,                    -- ULID
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    risk_level TEXT NOT NULL,               -- 'low', 'medium', 'high'
    proposed_by TEXT NOT NULL,              -- 'orchestrator', 'risk_manager', 'claude', 'system'
    status TEXT NOT NULL,                   -- 'pending', 'approved', 'rejected', 'expired'
    proposed_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT,                       -- 'user' or 'timeout'
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_log(status);
CREATE INDEX IF NOT EXISTS idx_approval_proposed_at ON approval_log(proposed_at);

-- ---------------------------------------------------------------------------
-- Briefings Table
-- ---------------------------------------------------------------------------
-- Pre-market and EOD briefings for The Debrief page (Sprint 21c)
CREATE TABLE IF NOT EXISTS briefings (
    id TEXT PRIMARY KEY,                    -- ULID
    date TEXT NOT NULL,                     -- YYYY-MM-DD
    briefing_type TEXT NOT NULL,            -- 'pre_market' or 'eod'
    status TEXT NOT NULL DEFAULT 'draft',   -- 'draft', 'final', 'ai_generated'
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    metadata TEXT,                          -- JSON
    author TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(date, briefing_type)
);

CREATE INDEX IF NOT EXISTS idx_briefings_date ON briefings(date);
CREATE INDEX IF NOT EXISTS idx_briefings_type ON briefings(briefing_type);
CREATE INDEX IF NOT EXISTS idx_briefings_status ON briefings(status);

-- ---------------------------------------------------------------------------
-- Journal Entries Table
-- ---------------------------------------------------------------------------
-- Learning journal for The Debrief page (Sprint 21c)
CREATE TABLE IF NOT EXISTS journal_entries (
    id TEXT PRIMARY KEY,                    -- ULID
    entry_type TEXT NOT NULL,               -- 'observation', 'trade_annotation', 'pattern_note', 'system_note'
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT 'user',
    linked_strategy_id TEXT,
    linked_trade_ids TEXT,                  -- JSON array
    tags TEXT,                              -- JSON array
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_journal_type ON journal_entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_journal_author ON journal_entries(author);
CREATE INDEX IF NOT EXISTS idx_journal_created ON journal_entries(created_at);

-- ---------------------------------------------------------------------------
-- Documents Table
-- ---------------------------------------------------------------------------
-- Database-stored documents for The Debrief page (Sprint 21c)
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,                    -- ULID
    category TEXT NOT NULL,                 -- 'research', 'strategy', 'backtest', 'ai_report'
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT 'user',
    tags TEXT,                              -- JSON array
    metadata TEXT,                          -- JSON
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at);

-- ---------------------------------------------------------------------------
-- Quality History Table
-- ---------------------------------------------------------------------------
-- Full component breakdown per scored signal (Sprint 24 — Quality Engine)
CREATE TABLE IF NOT EXISTS quality_history (
    id TEXT PRIMARY KEY,                    -- ULID
    symbol TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    scored_at TEXT NOT NULL,                -- ISO-8601 ET timestamp (DEC-276)

    -- Component dimension scores (each 0–100)
    pattern_strength REAL NOT NULL,
    catalyst_quality REAL NOT NULL,
    volume_profile REAL NOT NULL,
    historical_match REAL NOT NULL,
    regime_alignment REAL NOT NULL,

    -- Composite score and grade
    composite_score REAL NOT NULL,
    grade TEXT NOT NULL,
    risk_tier TEXT NOT NULL,

    -- Execution parameters
    entry_price REAL NOT NULL,
    stop_price REAL NOT NULL,
    calculated_shares INTEGER NOT NULL,

    -- Context
    signal_context TEXT,                    -- JSON dict with strategy-specific factors

    -- Outcome columns (NULL until trade closes)
    outcome_trade_id TEXT,
    outcome_realized_pnl REAL,
    outcome_r_multiple REAL,

    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_quality_history_symbol ON quality_history(symbol);
CREATE INDEX IF NOT EXISTS idx_quality_history_strategy ON quality_history(strategy_id);
CREATE INDEX IF NOT EXISTS idx_quality_history_scored_at ON quality_history(scored_at);
CREATE INDEX IF NOT EXISTS idx_quality_history_grade ON quality_history(grade);

-- ---------------------------------------------------------------------------
-- Execution Records Table
-- ---------------------------------------------------------------------------
-- Execution quality logging for slippage model calibration (DEC-358 §5.1)
CREATE TABLE IF NOT EXISTS execution_records (
    record_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    side TEXT NOT NULL,
    expected_fill_price REAL NOT NULL,
    expected_slippage_bps REAL NOT NULL,
    actual_fill_price REAL NOT NULL,
    actual_slippage_bps REAL NOT NULL,
    time_of_day TEXT NOT NULL,
    order_size_shares INTEGER NOT NULL,
    avg_daily_volume INTEGER,
    bid_ask_spread_bps REAL,
    latency_ms REAL,
    slippage_vs_model REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_execution_records_order ON execution_records(order_id);
CREATE INDEX IF NOT EXISTS idx_execution_records_strategy ON execution_records(strategy_id);
CREATE INDEX IF NOT EXISTS idx_execution_records_symbol ON execution_records(symbol);
CREATE INDEX IF NOT EXISTS idx_execution_records_created ON execution_records(created_at);

-- ---------------------------------------------------------------------------
-- System Health Table
-- ---------------------------------------------------------------------------
-- NOTE: Deferred to Step 10 (System Health Monitoring)
-- CREATE TABLE IF NOT EXISTS system_health (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     timestamp TEXT NOT NULL,
--     component TEXT NOT NULL,
--     status TEXT NOT NULL,                 -- 'healthy', 'degraded', 'down'
--     latency_ms REAL,
--     details TEXT
-- );
