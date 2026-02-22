# Sprint 14 — Session A Prompts (Python Backend)

Copy-paste each prompt sequentially into Claude Code.
Wait for all tests to pass before moving to the next prompt.

---

## Pre-Session Setup

Before Prompt 1, manually do these:

1. Copy the sprint spec into the repo:
   ```
   cp <wherever>/sprint_14_spec.md docs/sprints/sprint_14_spec.md
   ```

2. Copy the rules file:
   ```
   mkdir -p .claude/rules
   cp <wherever>/sprint_14_rules.md .claude/rules/sprint-14.md
   ```

3. Commit:
   ```
   git add docs/sprints/sprint_14_spec.md .claude/rules/sprint-14.md
   git commit -m "docs: add Sprint 14 spec and Claude rules"
   ```

---

## Prompt 1: Config + Dependencies + Project Structure

```
Sprint 14, Prompt 1 of 6 (Session A).

Read the full sprint spec at docs/sprints/sprint_14_spec.md — this is your implementation guide for the entire sprint. Also read .claude/rules/sprint-14.md for cross-cutting contracts.

This prompt: Config, dependencies, and project structure setup.

Tasks:
1. Add these Python dependencies (match the project's existing dependency management pattern — check pyproject.toml or requirements.txt): fastapi>=0.109, uvicorn[standard]>=0.27, python-jose[cryptography]>=3.3, passlib[bcrypt]>=1.7, httpx>=0.26 (as dev/test dependency if separated)

2. Create the ApiConfig Pydantic model (see spec Section 2.1 for exact fields). Put it alongside existing config models — check where SystemConfig, BrokerConfig, etc. live and follow the same pattern. Add `api: ApiConfig` field to SystemConfig with default `ApiConfig()` so existing configs without an `api` section still work.

3. Add the `api` section to config/system.yaml (see spec Section 2.3).

4. Create the directory structure with __init__.py files:
   - argus/api/__init__.py
   - argus/api/routes/__init__.py  
   - argus/api/websocket/__init__.py
   - tests/api/__init__.py
   - tests/analytics/__init__.py (if not exists)

5. Run the full existing test suite — confirm 811 tests still pass, zero regressions. The new config must be backward-compatible with existing SystemConfig usage.

Do NOT implement any route handlers or server logic yet — just the foundation.
```

---

## Prompt 2: Auth + Setup Password

```
Sprint 14, Prompt 2 of 6 (Session A).

Refer to docs/sprints/sprint_14_spec.md Sections 4.2, 4.3, and 4.5 (routes/auth.py).

This prompt: Authentication system and setup CLI.

Tasks:
1. Implement argus/api/auth.py — JWT creation, verification, password verification, and the `require_auth` FastAPI dependency. See spec Section 4.2 for the exact interface. Key details:
   - Algorithm: HS256
   - JWT secret resolved from environment variable named in config.api.jwt_secret_env
   - Token payload: {"exp": ..., "iat": ..., "sub": "operator"}
   - `require_auth` uses HTTPBearer and validates via verify_token
   - Handle missing JWT secret gracefully (500 with clear message)

2. Implement argus/api/setup_password.py — CLI tool per spec Section 4.3. Should work as `python -m argus.api.setup_password`.

3. Implement argus/api/routes/auth.py — Two endpoints:
   - POST /auth/login: accepts {"password": "string"}, verifies against config.api.password_hash, returns {"access_token", "token_type", "expires_at"}. Returns 401 on invalid.
   - POST /auth/refresh: requires valid token, returns new token with fresh expiry.
   
   This route file needs access to AppState for config — but AppState isn't fully built yet. For now, import get_app_state from dependencies.py and create a minimal version of that module with just the get/set functions and a placeholder AppState. We'll flesh it out in Prompt 3.

4. Create tests/api/conftest.py with shared fixtures per spec Section 6.1 and .claude/rules/sprint-14.md. The conftest needs:
   - api_config fixture (ApiConfig with bcrypt hash of "testpassword123")
   - jwt_secret fixture (monkeypatches ARGUS_JWT_SECRET env var)
   - auth_headers fixture (generates valid Bearer token)
   - A minimal app_state and client fixture — enough for auth tests to work. These get expanded in Prompt 3.

5. Write tests/api/test_auth.py — ~10 tests per spec Section 6.2. Test login success, wrong password, empty password, valid token access, expired token, invalid signature, missing token, refresh success, refresh with expired token, and setup_password hash generation.

All tests pass (existing 811 + ~10 new).
```

---

## Prompt 3: AppState + Server Factory + Account Endpoint

```
Sprint 14, Prompt 3 of 6 (Session A).

Refer to docs/sprints/sprint_14_spec.md Sections 4.1, 4.4, and 4.5 (routes/account.py).

This prompt: Full AppState, server factory, and account endpoint.

Tasks:
1. Flesh out argus/api/dependencies.py with the complete AppState dataclass per spec Section 4.1. Fields: event_bus, trade_logger, broker, health_monitor, risk_manager, order_manager, data_service, strategies (dict[str, BaseStrategy]), clock, config (SystemConfig), start_time (float). Include set_app_state() and get_app_state() module-level functions.

2. Implement argus/api/server.py per spec Section 4.4:
   - create_app(state: AppState) → FastAPI — lifespan context manager, CORS middleware, router mounting, optional static files
   - run_server(app, host, port) → asyncio.Task — programmatic uvicorn with signal handler override
   - The app should NOT mount static files if config.api.static_dir is empty

3. Update argus/api/routes/__init__.py to aggregate all route routers under api_router (even though most route files are stubs for now — create placeholder routers in the files we haven't implemented yet so the import works).

4. Implement argus/api/routes/account.py:
   - GET /account — requires auth
   - Sources: broker.get_account() for equity/cash/buying_power, trade_logger for daily P&L, clock for market status
   - Include the _get_market_status() helper (see spec Section 4.5)
   - Response shape per spec Section "REST API Schema" under GET /api/v1/account

5. Add the get_managed_positions() public method to OrderManager (see spec Section 4.5 under routes/positions.py). This is a simple method that flattens _managed_positions values into a list.

6. Expand the conftest.py fixtures to provide a full mock AppState with:
   - Real EventBus
   - Real TradeLogger connected to in-memory SQLite (or temp file), seeded with ~5-10 sample trades
   - SimulatedBroker with $100K account
   - Real HealthMonitor
   - Real RiskManager (default config)
   - Real OrderManager
   - SystemClock
   - Default SystemConfig with api section
   - At least one mock strategy in the strategies dict

7. Write tests/api/test_account.py (~5 tests) and tests/api/test_server.py (~5 tests) per spec Section 6.2.

All tests pass (existing 811 + ~20 cumulative new).
```

---

## Prompt 4: Positions + Trades Endpoints

```
Sprint 14, Prompt 4 of 6 (Session A).

Refer to docs/sprints/sprint_14_spec.md Section 4.5 (routes/positions.py and routes/trades.py).

This prompt: Positions and trades endpoints with TradeLogger query methods.

Tasks:
1. Add query methods to TradeLogger (argus/analytics/trade_log.py):
   - query_trades(strategy_id?, date_from?, date_to?, outcome?, limit=50, offset=0) → list[dict]
     - Builds WHERE clause dynamically. outcome: "win" = pnl_dollars > 0, "loss" = pnl_dollars < 0, "breakeven" = pnl_dollars == 0
     - date_from/date_to filter on entry_time. Order by entry_time DESC.
   - count_trades(strategy_id?, date_from?, date_to?, outcome?) → int
     - Same filters, returns count for pagination
   - get_daily_pnl(date_from?, date_to?) → list[dict]
     - Returns [{date, pnl, trades}] from strategy_daily_performance table aggregated across strategies
   - get_todays_pnl() → float
     - Today's total realized P&L

2. Implement argus/api/routes/positions.py:
   - GET /positions with optional ?strategy_id= filter
   - Source: order_manager.get_managed_positions()
   - Enrich each position with: current_price (from data_service.get_current_price), unrealized_pnl, unrealized_pnl_pct, hold_duration_seconds, r_multiple_current
   - Handle gracefully when data_service is None or get_current_price fails (use entry_price as fallback, set unrealized fields to 0)
   - Response shape per spec

3. Implement argus/api/routes/trades.py:
   - GET /trades with query params: strategy_id, date_from, date_to, outcome, limit (default 50), offset (default 0)
   - Source: trade_logger.query_trades() and trade_logger.count_trades()
   - Response includes total_count for pagination

4. Update conftest.py to seed the TradeLogger with enough sample trades to test filtering (at least 10-15 trades across different strategies, dates, outcomes).

5. Write tests/api/test_positions.py (~8 tests) and tests/api/test_trades.py (~10 tests) per spec Section 6.2.

All tests pass (existing 811 + ~38 cumulative new).
```

---

## Prompt 5: Performance Calculator + Performance Endpoint

```
Sprint 14, Prompt 5 of 6 (Session A).

Refer to docs/sprints/sprint_14_spec.md Sections 4.8 and 4.5 (routes/performance.py).

This prompt: Extract shared PerformanceCalculator and build performance endpoint.

Tasks:
1. Create argus/analytics/performance.py with PerformanceMetrics dataclass and compute_metrics(trades: list[dict]) function. See spec Section 4.8 and .claude/rules/sprint-14.md for the exact interface.

   IMPORTANT: Look at the existing argus/backtest/metrics.py first. Extract the core computation logic (win rate, profit factor, Sharpe ratio, max drawdown, consecutive wins/losses, etc.) into the new compute_metrics() function. The formulas must be identical — this is a refactor, not a rewrite.

   Key behaviors:
   - Only processes closed trades (exit_price is not None)
   - Returns zeroed PerformanceMetrics for empty input
   - profit_factor: gross_wins / abs(gross_losses), handle zero losses (return float('inf') or a large sentinel)
   - Sharpe: annualized from daily returns (mean / std * sqrt(252)), handle zero std
   - max_drawdown_pct: from cumulative P&L curve
   - consecutive_wins/losses: sequential scan

2. Refactor argus/backtest/metrics.py to import and use compute_metrics() from the new shared module where possible. This must be a zero-behavior-change refactor — all existing backtest tests must still pass unchanged.

3. Implement argus/api/routes/performance.py:
   - GET /performance/{period} where period = "today" | "week" | "month" | "all"
   - Map period to date range using clock.now() in ET timezone
   - Fetch trades via trade_logger.query_trades() for the date range
   - Compute metrics via compute_metrics()
   - Also return daily_pnl array and by_strategy breakdown
   - Return 422 for invalid period values
   - Response shape per spec

4. Write tests/analytics/test_performance.py (~10 tests) — unit tests for compute_metrics with various edge cases (empty, all wins, all losses, mixed, zero losses, open trades excluded, etc.)

5. Write tests/api/test_performance.py (~10 tests) — endpoint tests per spec Section 6.2.

6. Run the FULL test suite including all existing backtest tests — confirm zero regressions from the metrics extraction.

All tests pass (existing 811 + ~58 cumulative new).
```

---

## Prompt 6: Health + Strategies Endpoints

```
Sprint 14, Prompt 6 of 6 (Session A).

Refer to docs/sprints/sprint_14_spec.md Section 4.5 (routes/health.py and routes/strategies.py).

This prompt: Health and strategies endpoints. Final prompt of Session A.

Tasks:
1. Check the existing HealthMonitor (argus/core/health.py) for what public methods already exist. Add any needed methods:
   - get_component_statuses() → dict[str, dict] — returns {name: {status, details}} for all registered components
   - get_overall_status() → str — returns "healthy", "degraded", or "unhealthy" based on component statuses
   If these already exist under different names, use the existing ones and adapt the route.

2. Implement argus/api/routes/health.py:
   - GET /health — requires auth
   - Source: health_monitor methods, AppState.start_time for uptime
   - Include: last_heartbeat, last_trade (from trade_logger), last_data_received (from data_service if available)
   - paper_mode: derive from config (broker_source == "alpaca" or "simulated" → true)
   - Response shape per spec

3. Implement argus/api/routes/strategies.py:
   - GET /strategies — requires auth
   - Source: AppState.strategies dict
   - For each strategy: strategy_id, name, version, is_active, pipeline_stage, allocated_capital, daily_pnl, trade_count_today, open_positions count (from order_manager.get_managed_positions() filtered by strategy_id), config_summary
   - config_summary: extract key params from strategy.config (if OrbBreakout, include opening_range_minutes, max_hold_minutes, target_r, min_gap_pct)

4. Write tests/api/test_health.py (~5 tests) and tests/api/test_strategies.py (~5 tests) per spec Section 6.2.

5. Make sure all route placeholder stubs in routes/__init__.py are now replaced with real implementations. The api_router should include all 7 route modules: auth, account, positions, trades, performance, health, strategies.

6. Run the full test suite. Report the total test count.

After this prompt, Session A is complete. All REST endpoints are implemented and tested.
Expected total: ~811 + 68 = ~879 tests.

Session B (prompts 7-10) will add: WebSocket bridge, dev state, main.py integration, React scaffolding, and cleanup.
```

---

## End of Session A

After Prompt 6 completes:
1. Run `python -m pytest tests/ -v` — confirm all pass
2. Run `ruff check` — fix any issues
3. `git add -A && git commit -m "sprint-14: session A complete — API endpoints + auth + performance calculator"`
4. Proceed to Session B prompts
