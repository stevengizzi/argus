# Sprint 14 — Revised Session Prompts (Self-Contained)

## Status
- Prompt 1 COMPLETE: ApiConfig, SystemConfig updated, dependencies added, directory structure created, all 811 tests pass.
- Sessions below are numbered 1-7. Each is a fresh Claude Code session.
- Copy the rules file before starting: `.claude/rules/sprint_14_rules.md` (already provided separately)

## Code Review Checkpoints
- After Session 4 (all REST endpoints done) — review with Claude.ai
- After Session 7 (sprint complete) — final review with Claude.ai

---

## Session 1: Auth System + Test Fixtures

```
Sprint 14 — Auth System + Test Fixtures

CONTEXT: ARGUS trading system, 811 tests. Sprint 14 adds a Command Center API (FastAPI). The previous prompt already created ApiConfig (with fields: enabled, host, port, password_hash, jwt_secret_env, jwt_expiry_hours, cors_origins, ws_heartbeat_interval_seconds, ws_tick_throttle_ms, static_dir), added it to SystemConfig, created the argus/api/ directory structure, and installed dependencies (fastapi, uvicorn, python-jose, passlib, httpx).

YOUR TASK: Implement JWT authentication and create the shared test fixtures that all future API tests will use.

### 1. Create argus/api/auth.py

```python
# Exports: verify_password, create_access_token, verify_token, require_auth

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.hash import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

ALGORITHM = "HS256"
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.verify(plain_password, hashed_password)

def create_access_token(jwt_secret: str, expires_hours: int = 24) -> tuple[str, datetime]:
    """Create a JWT access token. Returns (token, expires_at)."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload = {"exp": expires_at, "iat": datetime.now(timezone.utc), "sub": "operator"}
    token = jwt.encode(payload, jwt_secret, algorithm=ALGORITHM)
    return token, expires_at

def verify_token(token: str, jwt_secret: str) -> dict:
    """Verify and decode a JWT. Raises HTTPException on failure."""
    try:
        return jwt.decode(token, jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

def resolve_jwt_secret(api_config) -> str:
    """Resolve JWT secret from environment variable named in config."""
    secret = os.environ.get(api_config.jwt_secret_env, "")
    if not secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")
    return secret

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """FastAPI dependency — validates JWT from Authorization header.
    NOTE: This needs the jwt_secret. Since it's a Depends(), we can't easily
    inject AppState here. Use a module-level variable set during app startup,
    or resolve from env var directly. Choose the cleanest approach that works
    with FastAPI's DI system."""
    # Implementation note: you may need to either:
    # (a) Use a module-level _jwt_secret variable set during app lifespan, or
    # (b) Make require_auth a closure/class that captures config, or
    # (c) Have routes pass config explicitly
    # Pick the approach that keeps route handlers clean: _auth: dict = Depends(require_auth)
```

### 2. Create argus/api/setup_password.py

CLI tool that prompts for a password and prints the bcrypt hash + instructions.
Run as: `python -m argus.api.setup_password`
- Use getpass for password input
- Confirm password (enter twice)
- Minimum 8 characters
- Print the bcrypt hash and instructions to add it to config/system.yaml
- Also print instruction to set ARGUS_JWT_SECRET env var

### 3. Create argus/api/routes/auth.py

```python
router = APIRouter()

# POST /login
# Request: {"password": "string"}
# Verify against state.config.api.password_hash using verify_password()
# On success: return {"access_token": "...", "token_type": "bearer", "expires_at": "ISO8601"}
# On failure: 401 {"detail": "Invalid credentials"}

# POST /refresh
# Requires valid token (use require_auth dependency)
# Returns new token with fresh expiry
```

This route needs access to AppState for config. Create the minimal dependencies module needed:

### 4. Create argus/api/dependencies.py

```python
from dataclasses import dataclass

@dataclass
class AppState:
    """Holds references to all trading engine components for API access."""
    event_bus: ...       # EventBus
    trade_logger: ...    # TradeLogger
    broker: ...          # Broker
    health_monitor: ...  # HealthMonitor
    risk_manager: ...    # RiskManager
    order_manager: ...   # OrderManager
    data_service: ...    # DataService | None
    strategies: dict     # dict[str, BaseStrategy]
    clock: ...           # Clock
    config: ...          # SystemConfig
    start_time: float = 0.0

# Use typing.Any or actual imports for the type hints — follow existing project patterns.
# Module-level get/set:
_app_state: AppState | None = None

def set_app_state(state: AppState) -> None: ...
def get_app_state() -> AppState: ...  # Raises RuntimeError if not set
```

### 5. Create tests/api/conftest.py

Shared fixtures for all API tests:

```python
import pytest
import pytest_asyncio
from passlib.hash import bcrypt

# Fixtures needed:

@pytest.fixture
def api_config():
    """ApiConfig with bcrypt hash of 'testpassword123'."""
    # Return ApiConfig(password_hash=bcrypt.hash("testpassword123"), ...)

@pytest.fixture
def jwt_secret(monkeypatch):
    """Set ARGUS_JWT_SECRET env var. Return the secret string."""
    secret = "test-secret-key-for-jwt-signing-min-32-chars"
    monkeypatch.setenv("ARGUS_JWT_SECRET", secret)
    return secret

@pytest.fixture
def auth_headers(jwt_secret):
    """Valid Authorization headers."""
    from argus.api.auth import create_access_token
    token, _ = create_access_token(jwt_secret)
    return {"Authorization": f"Bearer {token}"}

# For now, create minimal app_state and client fixtures — enough for auth tests.
# These get expanded in future sessions. The client fixture should use:
#   httpx.AsyncClient with ASGITransport wrapping the FastAPI app.
# For auth tests, app_state needs: config (with api section).
# Other fields can be None or simple mocks for now — auth routes only need config.
```

### 6. Write tests/api/test_auth.py (~10 tests)

- test_login_success — correct password → 200 + token
- test_login_wrong_password — wrong password → 401
- test_login_empty_password — empty string → 401
- test_protected_endpoint_with_valid_token — can access a protected route (use /account or create a test route)
- test_expired_token_rejected — create token with expires_hours=-1 → 401
- test_invalid_signature_rejected — token signed with wrong secret → 401
- test_missing_auth_header — no Authorization header → 401 or 403
- test_refresh_returns_new_token — valid token → new token with later expiry
- test_refresh_with_expired_token — expired token → 401
- test_bcrypt_hash_generation — verify setup_password's hash function works

Run full test suite: all 811 existing + ~10 new tests pass.
```

---

## Session 2: Server Factory + Account Endpoint

```
Sprint 14 — Server Factory + Account Endpoint

CONTEXT: ARGUS trading system. Sprint 14 adds Command Center API. Previous sessions completed: ApiConfig, dependencies, directory structure, JWT auth (auth.py, routes/auth.py), AppState dataclass, test conftest with auth fixtures. All tests passing.

YOUR TASK: Build the FastAPI server factory and the first data endpoint (account).

### 1. Implement argus/api/server.py

```python
"""ARGUS API Server — FastAPI application factory."""

def create_app(state: AppState) -> FastAPI:
    """Create the FastAPI app.
    - Use lifespan context manager to call set_app_state(state) on startup
    - Add CORSMiddleware with origins from state.config.api.cors_origins
    - Include api_router under prefix /api/v1
    - Include ws_router (no prefix) — create a placeholder ws_router for now
    - If state.config.api.static_dir is non-empty, mount StaticFiles at /
    """

async def run_server(app: FastAPI, host: str, port: int) -> asyncio.Task:
    """Start uvicorn programmatically in the existing event loop.
    - Use uvicorn.Config + uvicorn.Server
    - Override server.install_signal_handlers = lambda: None (avoid conflict with main.py)
    - Return the asyncio.Task so caller can cancel it on shutdown
    """
```

Also make it runnable standalone (this will be fleshed out later, but stub it):
`python -m argus.api.server` — for now, just print "Use --dev flag" and exit.

### 2. Create argus/api/routes/__init__.py

Aggregate all route routers. For routes not yet implemented (positions, trades, performance, health, strategies), create the file with just an empty `router = APIRouter()` so the import works.

```python
from fastapi import APIRouter
# Import all route routers
api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(account_router, tags=["account"])
api_router.include_router(positions_router, tags=["positions"])
api_router.include_router(trades_router, tags=["trades"])
api_router.include_router(performance_router, tags=["performance"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(strategies_router, tags=["strategies"])
```

### 3. Implement argus/api/routes/account.py

```python
router = APIRouter()

# GET /account — requires auth
# Response shape:
{
    "equity": float,          # from broker.get_account()
    "cash": float,            # from broker.get_account()
    "buying_power": float,    # from broker.get_account()
    "daily_pnl": float,       # from trade_logger (today's closed trades sum)
    "daily_pnl_pct": float,   # daily_pnl / equity * 100
    "open_positions_count": int,  # from order_manager.get_managed_positions()
    "daily_trades_count": int,    # from trade_logger (today's trade count)
    "market_status": str,     # "pre_market", "open", "closed", "after_hours"
    "broker_source": str,     # from config.broker_source
    "data_source": str,       # from config.data_source
    "timestamp": str          # ISO 8601 UTC
}
```

Market status logic (use ET timezone):
- Weekday: 4:00-9:30 = pre_market, 9:30-16:00 = open, 16:00-20:00 = after_hours, else closed
- Weekend: always closed

For daily_pnl: query today's trades from TradeLogger. If TradeLogger doesn't have a method for this yet, add a simple one: `get_todays_pnl() -> float` and `get_todays_trade_count() -> int`. Use date comparison in ET timezone.

### 4. Add public method to OrderManager

Add to argus/execution/order_manager.py:
```python
def get_managed_positions(self) -> list[ManagedPosition]:
    """Return a snapshot of all managed positions (for API/UI)."""
    result = []
    for positions in self._managed_positions.values():
        result.extend(positions)
    return result
```

### 5. Expand conftest.py

The test fixtures now need a more complete AppState:
- Real EventBus
- Real TradeLogger with in-memory SQLite, seeded with 5-10 sample closed trades (mix of wins/losses, different dates including today)
- SimulatedBroker with $100K account
- Real HealthMonitor (or mock with get_component_statuses/get_overall_status)
- Real RiskManager (default config)
- Real OrderManager
- SystemClock (or FixedClock set to a known market-hours time for deterministic tests)
- Default SystemConfig with api section
- strategies dict with one mock/real OrbBreakout strategy

Use existing test patterns from the codebase for creating these components.

### 6. Write tests

tests/api/test_server.py (~5 tests):
- test_app_creation — create_app returns FastAPI
- test_cors_headers — OPTIONS request returns CORS headers
- test_routes_under_api_v1 — /api/v1/account exists
- test_openapi_available — /docs returns 200
- test_static_not_mounted_when_empty — no static_dir config → / doesn't serve files

tests/api/test_account.py (~5 tests):
- test_get_account_success — returns correct shape with values from mock broker
- test_account_daily_pnl — daily_pnl reflects today's trades
- test_account_market_status_during_hours — returns "open" when clock is during market
- test_account_market_status_after_hours — returns "closed" when clock is outside market
- test_account_unauthenticated — 401 without token

All tests pass.
```

---

## Session 3: Positions + Trades Endpoints

```
Sprint 14 — Positions + Trades Endpoints

CONTEXT: ARGUS Sprint 14. Previous sessions completed: config, auth, server factory, account endpoint, AppState, conftest fixtures with seeded TradeLogger. All tests passing.

YOUR TASK: Build the positions and trades endpoints, including new TradeLogger query methods.

### 1. Add query methods to TradeLogger (argus/analytics/trade_log.py)

Add these async methods to the existing TradeLogger class:

```python
async def query_trades(
    self,
    strategy_id: str | None = None,
    date_from: str | None = None,   # ISO date "2026-02-01"
    date_to: str | None = None,     # ISO date "2026-02-22"
    outcome: str | None = None,     # "win" | "loss" | "breakeven"
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Query trades with filtering and pagination. Ordered by entry_time DESC."""
    # Build WHERE clause dynamically with parameterized queries (no SQL injection!)
    # outcome mapping: "win" = pnl_dollars > 0, "loss" = pnl_dollars < 0, "breakeven" = pnl_dollars = 0
    # date_from/date_to filter on entry_time (compare date portion)
    # Return list of dicts (column names as keys)

async def count_trades(
    self,
    strategy_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    outcome: str | None = None,
) -> int:
    """Count trades matching filters (for pagination total)."""

async def get_daily_pnl(
    self,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Get daily P&L aggregation: [{date, pnl, trades}].
    Source: aggregate from trades table grouped by date(entry_time).
    Or from strategy_daily_performance if populated."""

async def get_todays_trade_count(self) -> int:
    """Count of today's trades (ET timezone)."""
```

If `get_todays_pnl()` was added in Session 2, keep it. Add `get_todays_trade_count()` if not already present.

### 2. Implement argus/api/routes/positions.py

```python
router = APIRouter()

# GET /positions?strategy_id=optional_filter
# Requires auth
# Source: order_manager.get_managed_positions()
# For each ManagedPosition, compute:
#   current_price: try data_service.get_current_price(symbol), fallback to entry_price
#   unrealized_pnl: (current_price - entry_price) * shares_remaining
#   unrealized_pnl_pct: unrealized_pnl / (entry_price * shares_remaining) * 100
#   hold_duration_seconds: (clock.now() - entry_time).total_seconds()
#   r_multiple_current: (current_price - entry_price) / (entry_price - stop_price)
#     Guard against division by zero if entry_price == stop_price

# Response:
{
    "positions": [
        {
            "position_id": str,
            "strategy_id": str,
            "symbol": str,
            "side": "long",
            "entry_price": float,
            "entry_time": str,  # ISO 8601
            "shares_total": int,
            "shares_remaining": int,
            "current_price": float,
            "unrealized_pnl": float,
            "unrealized_pnl_pct": float,
            "stop_price": float,
            "t1_price": float,
            "t2_price": float,
            "t1_filled": bool,
            "hold_duration_seconds": int,
            "r_multiple_current": float
        }
    ],
    "count": int,
    "timestamp": str
}
```

Handle data_service being None (dev mode / some test scenarios) — use entry_price as current_price fallback.

### 3. Implement argus/api/routes/trades.py

```python
router = APIRouter()

# GET /trades?strategy_id=&date_from=&date_to=&outcome=&limit=50&offset=0
# Requires auth
# Source: trade_logger.query_trades() + trade_logger.count_trades()

# Response:
{
    "trades": [
        {
            "id": str,
            "strategy_id": str,
            "symbol": str,
            "side": str,
            "entry_price": float,
            "entry_time": str,
            "exit_price": float | null,
            "exit_time": str | null,
            "shares": int,
            "pnl_dollars": float | null,
            "pnl_r_multiple": float | null,
            "exit_reason": str | null,
            "hold_duration_seconds": int | null,
            "commission": float,
            "market_regime": str | null
        }
    ],
    "total_count": int,   # total matching trades (for pagination)
    "limit": int,
    "offset": int,
    "timestamp": str
}
```

### 4. Update conftest.py

Ensure the seeded TradeLogger has enough variety for filtering tests:
- At least 15 trades across different dates (last 30 days), strategies, and outcomes
- Include some trades from today (for daily_pnl tests)
- Include both wins and losses
- Include different exit_reasons

Add a fixture that injects ManagedPositions into the OrderManager for position tests.

### 5. Write tests

tests/api/test_positions.py (~8 tests):
- test_positions_empty — no managed positions → empty list
- test_positions_with_data — mock positions → correct shape and enrichment
- test_positions_filter_by_strategy — strategy_id param works
- test_positions_computed_unrealized_pnl — math is correct
- test_positions_computed_r_multiple — math is correct
- test_positions_hold_duration — seconds calculated correctly
- test_positions_data_service_none — handles missing data service gracefully
- test_positions_unauthenticated — 401

tests/api/test_trades.py (~10 tests):
- test_trades_default — returns up to 50 most recent
- test_trades_pagination — limit=5, offset=5 returns next page
- test_trades_filter_strategy — strategy_id filter works
- test_trades_filter_date_range — date_from + date_to work
- test_trades_filter_outcome_win — outcome=win returns only profitable trades
- test_trades_filter_outcome_loss — outcome=loss returns only losing trades
- test_trades_combined_filters — multiple filters together
- test_trades_empty_result — no matches → empty list, total_count=0
- test_trades_total_count_for_pagination — total_count is correct
- test_trades_unauthenticated — 401

All tests pass.
```

---

## Session 4: Performance Calculator + Performance Endpoint

```
Sprint 14 — Performance Calculator + Performance Endpoint

CONTEXT: ARGUS Sprint 14. Previous sessions completed: config, auth, server, account, positions, trades endpoints. TradeLogger has query methods. All tests passing.

YOUR TASK: Extract shared performance metric computation from backtest module and build the performance endpoint.

### 1. Create argus/analytics/performance.py

This module provides shared metric computation used by both the API and the backtesting toolkit.

```python
from dataclasses import dataclass
import math

@dataclass
class PerformanceMetrics:
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0      # gross_wins / abs(gross_losses). inf if no losses.
    net_pnl: float = 0.0
    gross_pnl: float = 0.0
    total_commissions: float = 0.0
    avg_r_multiple: float = 0.0
    sharpe_ratio: float = 0.0       # annualized: mean(daily_returns) / std * sqrt(252)
    max_drawdown_pct: float = 0.0   # peak-to-trough on cumulative P&L
    avg_hold_seconds: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    consecutive_wins_max: int = 0
    consecutive_losses_max: int = 0

def compute_metrics(trades: list[dict]) -> PerformanceMetrics:
    """Compute metrics from trade dicts.
    Expected keys: pnl_dollars, pnl_r_multiple, commission, hold_duration_seconds, exit_price.
    Only closed trades (exit_price not None) are included."""
```

IMPORTANT: Before writing this, read argus/backtest/metrics.py. It already computes many of these metrics. Extract the computation logic so formulas are identical. If backtest/metrics.py uses a different input format (DataFrame vs list[dict]), adapt but keep formulas the same.

After creating performance.py, refactor backtest/metrics.py to import from it where possible. This must be a zero-behavior-change refactor — all existing backtest tests must pass unchanged. If the refactor is complex, skip it and just ensure the formulas match. Don't break existing code for a refactor.

### 2. Implement argus/api/routes/performance.py

```python
router = APIRouter()

# GET /performance/{period}
# period: "today" | "week" | "month" | "all"
# Requires auth

# Map period to date range using clock (ET timezone):
#   today: today's date
#   week: Monday of current week to today
#   month: 1st of current month to today
#   all: no date filter
# Invalid period → 422

# Fetch trades via trade_logger.query_trades(date_from=..., date_to=..., limit=10000)
# Compute metrics via compute_metrics()
# Also fetch daily_pnl via trade_logger.get_daily_pnl(date_from, date_to)
# Build by_strategy breakdown: group trades by strategy_id, compute metrics per group

# Response:
{
    "period": str,
    "date_from": str,   # ISO date
    "date_to": str,     # ISO date
    "metrics": {
        "total_trades": int,
        "win_rate": float,
        "profit_factor": float,
        "net_pnl": float,
        "gross_pnl": float,
        "total_commissions": float,
        "avg_r_multiple": float,
        "sharpe_ratio": float,
        "max_drawdown_pct": float,
        "avg_hold_seconds": float,
        "largest_win": float,
        "largest_loss": float,
        "consecutive_wins_max": int,
        "consecutive_losses_max": int
    },
    "daily_pnl": [{"date": str, "pnl": float, "trades": int}],
    "by_strategy": {
        "orb_breakout": {
            "total_trades": int,
            "win_rate": float,
            "net_pnl": float,
            "profit_factor": float
        }
    },
    "timestamp": str
}
```

### 3. Write tests

tests/analytics/test_performance.py (~10 tests):
- test_empty_trades — returns zeroed PerformanceMetrics
- test_all_wins — 100% win rate, profit_factor = inf
- test_all_losses — 0% win rate
- test_mixed_trades — realistic mix, verify win_rate and profit_factor
- test_profit_factor_no_losses — handles division by zero
- test_sharpe_ratio — verify against known data (or just verify it's a reasonable number and doesn't error)
- test_max_drawdown — known equity curve → known drawdown
- test_consecutive_streaks — verify max consecutive wins/losses
- test_open_trades_excluded — trades without exit_price skipped
- test_commission_summing — total_commissions correct

tests/api/test_performance.py (~10 tests):
- test_performance_today — returns today's metrics
- test_performance_week — returns week metrics
- test_performance_month — returns month metrics
- test_performance_all — returns all-time metrics
- test_invalid_period — "yearly" → 422
- test_empty_period — no trades in range → zeroed metrics
- test_daily_pnl_array — correct entries
- test_by_strategy_breakdown — matches per-strategy data
- test_win_rate_matches_data — verify against seeded trades
- test_unauthenticated — 401

Run FULL test suite including all backtest tests — confirm zero regressions.
All tests pass.
```

---

## Session 5: Health + Strategies Endpoints

```
Sprint 14 — Health + Strategies Endpoints

CONTEXT: ARGUS Sprint 14. Previous sessions completed: config, auth, server, account, positions, trades, performance endpoints + PerformanceCalculator. All tests passing.

YOUR TASK: Build the health and strategies endpoints. These are the last two REST endpoints. After this session, all 7 REST endpoints are complete.

### 1. Check HealthMonitor public API

Read argus/core/health.py. Check what methods already exist for:
- Getting all component statuses
- Getting overall system status
- Getting last heartbeat time

Add any missing public methods:
```python
def get_component_statuses(self) -> dict[str, dict]:
    """Return {component_name: {"status": "healthy"|"degraded"|"unhealthy", "details": str}}"""

def get_overall_status(self) -> str:
    """Return overall status: unhealthy if any unhealthy, degraded if any degraded, else healthy."""
```

If equivalent methods exist under different names, use those — don't add duplicates.

### 2. Implement argus/api/routes/health.py

```python
router = APIRouter()

# GET /health — requires auth
# Response:
{
    "status": str,               # "healthy", "degraded", "unhealthy"
    "uptime_seconds": int,       # time.time() - state.start_time
    "components": {
        "event_bus": {"status": str, "details": str},
        "data_service": {"status": str, "details": str},
        "broker": {"status": str, "details": str},
        "order_manager": {"status": str, "details": str},
        "risk_manager": {"status": str, "details": str},
        "database": {"status": str, "details": str}
    },
    "last_heartbeat": str | null,     # ISO 8601
    "last_trade": str | null,         # from trade_logger — most recent trade's exit_time
    "last_data_received": str | null,  # from data_service if available
    "paper_mode": bool,               # true if broker_source is "alpaca" or "simulated"
    "timestamp": str
}
```

For last_trade: query the most recent trade from TradeLogger (you may need to add a simple method or use query_trades with limit=1).
For last_data_received: if data_service has a last_update timestamp, use it. Otherwise null.
paper_mode: derive from config — if broker_source is "ibkr", it's false; otherwise true.

### 3. Implement argus/api/routes/strategies.py

```python
router = APIRouter()

# GET /strategies — requires auth
# Source: state.strategies dict
# Response:
{
    "strategies": [
        {
            "strategy_id": str,
            "name": str,
            "version": str,
            "is_active": bool,
            "pipeline_stage": str,    # "paper", "live", "concept", etc.
            "allocated_capital": float,
            "daily_pnl": float,
            "trade_count_today": int,
            "open_positions": int,    # count from order_manager filtered by strategy_id
            "config_summary": dict    # key config params
        }
    ],
    "count": int,
    "timestamp": str
}
```

For open_positions: filter order_manager.get_managed_positions() by strategy_id and count.
For config_summary: extract key params from strategy.config. Try to get common attributes like opening_range_minutes, max_hold_minutes, target_r, min_gap_pct. If config is a Pydantic model, use .model_dump() with include= to select key fields. If it's a different type, adapt.
For daily_pnl and trade_count_today: use strategy's own attributes if they exist, or query TradeLogger.

### 4. Verify route aggregation

Make sure argus/api/routes/__init__.py includes all 7 routers (auth, account, positions, trades, performance, health, strategies) and they're all real implementations now (no more placeholder empty routers).

### 5. Write tests

tests/api/test_health.py (~5 tests):
- test_health_all_healthy — all components healthy → status "healthy"
- test_health_degraded — one degraded component → overall "degraded"
- test_health_uptime — uptime_seconds is reasonable (> 0)
- test_health_paper_mode — matches config
- test_health_unauthenticated — 401

tests/api/test_strategies.py (~5 tests):
- test_strategies_list — returns all strategies
- test_strategies_fields — each strategy has required fields
- test_strategies_config_summary — config_summary has content
- test_strategies_open_positions_count — matches actual positions
- test_strategies_unauthenticated — 401

All tests pass. Report total test count.

THIS COMPLETES ALL REST ENDPOINTS. After this session, do a code review with Claude.ai before proceeding to Session 6 (WebSocket).
```

---

## Session 6: WebSocket Bridge

```
Sprint 14 — WebSocket Bridge

CONTEXT: ARGUS Sprint 14. All 7 REST endpoints complete and tested. This session adds real-time event streaming via WebSocket.

YOUR TASK: Build the Event Bus → WebSocket bridge that streams trading events to frontend clients.

### 1. Create argus/api/serializers.py

```python
def serialize_event(event) -> dict:
    """Convert an Event dataclass to a JSON-serializable dict.
    - Use dataclasses.asdict() for conversion
    - Convert datetime objects to ISO 8601 strings (recursively)
    - Remove 'sequence' from data (it goes in the wrapper message, not the payload)
    - Handle nested dataclasses (e.g., OrderApprovedEvent contains SignalEvent)
    - Fallback to event.__dict__ if asdict() fails
    """
```

### 2. Create argus/api/websocket/live.py

This is the most complex component. Key classes:

**ClientConnection:**
- Holds: websocket reference, subscribed_types (set or None for all), send_queue (asyncio.Queue, maxsize=1000)
- Method: wants_event(ws_type: str) → bool

**WebSocketBridge (singleton):**
- Manages list of ClientConnection objects
- On start(event_bus, order_manager, config):
  - Subscribe to these Event Bus event types:
    PositionOpenedEvent, PositionClosedEvent, PositionUpdatedEvent,
    OrderSubmittedEvent, OrderFilledEvent, OrderCancelledEvent,
    CircuitBreakerEvent, HeartbeatEvent, WatchlistEvent,
    SignalEvent, OrderApprovedEvent, OrderRejectedEvent
  - Subscribe to TickEvent separately (throttled handling)
  - Start heartbeat loop

- Event type mapping (internal class name → WS type string):
    PositionOpenedEvent → "position.opened"
    PositionClosedEvent → "position.closed"
    PositionUpdatedEvent → "position.updated"
    OrderSubmittedEvent → "order.submitted"
    OrderFilledEvent → "order.filled"
    OrderCancelledEvent → "order.cancelled"
    CircuitBreakerEvent → "system.circuit_breaker"
    HeartbeatEvent → "system.heartbeat"
    WatchlistEvent → "scanner.watchlist"
    SignalEvent → "strategy.signal"
    OrderApprovedEvent → "order.approved"
    OrderRejectedEvent → "order.rejected"

- TickEvent handling (special):
    - Only forward for symbols with open positions (check order_manager.get_managed_positions())
    - Throttle to max 1 per ws_tick_throttle_ms per symbol (use time.monotonic())
    - WS type: "price.update"
    - Data: {symbol, price, volume}

- Broadcast: enqueue message to each client's send_queue if client.wants_event(type)
  - On QueueFull: log warning, drop message (don't block)

- Heartbeat loop: send {"type": "system.heartbeat", "data": {"status": "alive"}} every ws_heartbeat_interval_seconds

**WebSocket message format (server → client):**
```json
{"type": "position.opened", "data": {...}, "sequence": 12345, "timestamp": "ISO8601"}
```

**WebSocket endpoint:**
```python
@ws_router.websocket("/ws/v1/live")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # 1. Authenticate: verify_token(token, jwt_secret). On failure: close with code 4001.
    # 2. Accept connection
    # 3. Create ClientConnection, add to bridge
    # 4. Start sender task (drains send_queue, sends to websocket)
    # 5. Receiver loop:
    #    - {"action": "ping"} → send {"type": "pong", "timestamp": "..."}
    #    - {"action": "subscribe", "types": [...]} → set client.subscribed_types
    #    - {"action": "unsubscribe", "types": [...]} → remove from subscribed_types
    # 6. On disconnect: cancel sender task, remove client from bridge
```

IMPORTANT: The ws_router must be included in the app WITHOUT the /api/v1 prefix. The endpoint path is /ws/v1/live. Check server.py — if it mounts ws_router separately from api_router, good. If not, fix the mounting.

Module-level singleton:
```python
_bridge: WebSocketBridge | None = None
def get_bridge() -> WebSocketBridge: ...
```

### 3. Write tests/api/test_websocket.py (~12 tests)

Use starlette's TestClient websocket_connect() or httpx WebSocket support:

- test_ws_connect_valid_token — accepted
- test_ws_connect_invalid_token — closed with 4001
- test_ws_connect_missing_token — rejected
- test_ws_receive_position_opened — publish PositionOpenedEvent on EventBus → client gets {"type": "position.opened", ...}
- test_ws_receive_order_filled — publish OrderFilledEvent → client gets it
- test_ws_tick_throttling — publish 50 TickEvents for same symbol rapidly → client gets ≤2
- test_ws_tick_position_filter — TickEvent for symbol with no position → client gets nothing
- test_ws_subscribe_filter — subscribe to ["position.opened"] → only gets that type
- test_ws_unsubscribe — unsubscribe from type → stops getting it
- test_ws_ping_pong — send ping → get pong with timestamp
- test_ws_heartbeat — configure 1-second heartbeat, wait, verify received
- test_ws_multiple_clients — two connected clients both receive same event

For tests that need ManagedPositions (tick filtering): inject positions into OrderManager in the fixture.
For tests that publish events: use the real EventBus from AppState and call event_bus.publish().

All tests pass.
```

---

## Session 7: Dev State + main.py Integration + React Scaffolding + Cleanup

```
Sprint 14 — Dev State + main.py + React + Final Cleanup

CONTEXT: ARGUS Sprint 14. All REST endpoints + WebSocket bridge complete and tested. This is the FINAL session.

YOUR TASK: Build the dev server mode, integrate API into main.py, scaffold the React frontend, and do final cleanup.

### Part A: Dev State

Create argus/api/dev_state.py:

```python
async def create_dev_state() -> AppState:
    """Create AppState with realistic mock data for frontend development."""
```

This should provide:
- Real EventBus
- Real TradeLogger connected to temp SQLite, seeded with ~20 trades over last 30 days:
  - Mix: ~55% wins, ~40% losses, ~5% breakeven
  - Exit reasons: target_1, stop_loss, time_stop, eod
  - Symbols: TSLA, NVDA, AAPL, AMD, META
  - strategy_id: "orb_breakout"
  - Realistic prices and hold durations
- SimulatedBroker with $100K
- Real HealthMonitor (all components HEALTHY)
- Real RiskManager (default config)
- Real OrderManager with 2-3 injected ManagedPosition objects (realistic values)
- strategies dict: {"orb_breakout": <strategy instance or mock>}
  - Needs: strategy_id, name, version, is_active=True, pipeline_stage="paper", allocated_capital=100000, daily_pnl, trade_count_today, config with ORB params
  - If OrbBreakoutStrategy constructor is complex, create a simple dataclass mock
- SystemClock
- SystemConfig with api.password_hash = bcrypt.hash("argus")
- Set ARGUS_JWT_SECRET env var within the function
- start_time = time.time()

### Part B: Standalone Entry

Create argus/api/__main__.py so `python -m argus.api.server --dev` works:

```python
import argparse, asyncio, uvicorn

def main():
    parser = argparse.ArgumentParser(description="ARGUS API Server")
    parser.add_argument("--dev", action="store_true", help="Mock data mode")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.dev:
        from argus.api.dev_state import create_dev_state
        from argus.api.server import create_app
        state = asyncio.run(create_dev_state())
        app = create_app(state)
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        print("Non-dev standalone mode not supported. Use --dev or start via main.py.")

if __name__ == "__main__":
    main()
```

Note: The module path `python -m argus.api.server` may need adjustment — the __main__.py might need to be at `argus/api/__main__.py` for `python -m argus.api` to work. Check Python's module execution rules and pick the right location.

### Part C: main.py Integration

Add Phase 11 to argus/main.py — after Phase 10 (data streaming):

```python
# Phase 11: API Server (optional)
if config.api.enabled:
    from argus.api.server import create_app, run_server
    from argus.api.dependencies import AppState, set_app_state
    from argus.api.websocket.live import get_bridge

    app_state = AppState(
        event_bus=event_bus,
        trade_logger=trade_logger,
        broker=broker,
        health_monitor=health_monitor,
        risk_manager=risk_manager,
        order_manager=order_manager,
        data_service=data_service,
        strategies={"orb_breakout": strategy},  # use actual strategy dict
        clock=clock,
        config=config,
        start_time=time.time(),
    )
    api_app = create_app(app_state)
    ws_bridge = get_bridge()
    await ws_bridge.start(event_bus, order_manager, config)
    api_task = await run_server(api_app, config.api.host, config.api.port)
    logger.info("Phase 11: API server started on %s:%d", config.api.host, config.api.port)
else:
    api_task = None
    logger.info("Phase 11: API server disabled")
```

Shutdown addition (before existing shutdowns):
```python
if api_task:
    api_task.cancel()
    try: await api_task
    except asyncio.CancelledError: pass
    await get_bridge().stop()
    logger.info("API server stopped")
```

Handle gracefully: if ARGUS_JWT_SECRET env var is not set, log a warning but don't crash the trading engine. The API just won't be usable until the secret is set.

### Part D: React Scaffolding

Initialize the React project in argus/ui/:

```bash
cd argus/ui
npm create vite@latest . -- --template react-ts
npm install react-router-dom zustand @tanstack/react-query recharts lucide-react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

If node/npm are not available, install them first.

Configure:
- vite.config.ts: proxy /api → localhost:8000, proxy /ws → ws://localhost:8000
- tailwind.config.js: content paths, custom colors:
  argus-bg: '#0f1117', argus-surface: '#1a1d27', argus-border: '#2a2d3a',
  argus-text: '#e1e4eb', argus-text-dim: '#8b8fa3', argus-accent: '#3b82f6',
  argus-success: '#22c55e', argus-danger: '#ef4444', argus-warning: '#f59e0b'
- src/index.css: Tailwind directives + body { @apply bg-argus-bg text-argus-text }

Create TypeScript files:
- src/api/types.ts — interfaces for all API responses (AccountInfo, Position, Trade, PerformanceMetrics, etc.)
- src/api/client.ts — fetch wrapper with JWT header, all endpoint methods
- src/api/ws.ts — reconnecting WebSocket with backoff
- src/stores/auth.ts — Zustand: token, isAuthenticated, login, logout, init from localStorage
- src/stores/live.ts — Zustand: connected, lastMessage, recentEvents
- src/components/ProtectedRoute.tsx — redirects to /login if not auth'd
- src/pages/Login.tsx — dark-themed login form
- src/pages/ConnectionTest.tsx — dev page that hits all endpoints and shows JSON results + WebSocket status
- src/App.tsx — Router: /login, / → ProtectedRoute → ConnectionTest, /dev/connection
- src/main.tsx — render App

Add to .gitignore: argus/ui/node_modules/, argus/ui/dist/

### Part E: Final Cleanup

1. Run ruff check on all new Python files — fix issues
2. Run full test suite: python -m pytest tests/ -v --tb=short
3. Report exact test count (target: ~890-910)
4. Verify zero regressions from 811 baseline
5. Verify: cd argus/ui && npm run build succeeds
6. Update CLAUDE.md:
   - Current State: "Sprint 14 (Command Center API) COMPLETE. [N] tests."
   - Components: add API server, WebSocket bridge, JWT auth, PerformanceCalculator
   - Commands: add setup_password, server --dev, npm commands
   - Dependencies: add fastapi, uvicorn, python-jose, passlib
7. Update docs/03_ARCHITECTURE.md Section 4: add "Implementation Status: Sprint 14 ✅ COMPLETE"

### Smoke Test

If possible, run this end-to-end verification:
```bash
python -m argus.api.server --dev &
sleep 3
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" -d '{"password":"argus"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/account | python3 -m json.tool
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/positions | python3 -m json.tool
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/health | python3 -m json.tool
kill %1
```

Sprint 14 is COMPLETE after this session.
```

---

## Post-Sprint

1. `git add -A && git commit -m "sprint-14: Command Center API + React scaffolding"`
2. Push to GitHub
3. Final code review with Claude.ai (Session 7 review brief)
4. Apply doc updates from review
5. Sync Claude.ai project
6. Optionally remove .claude/rules/sprint_14_rules.md
