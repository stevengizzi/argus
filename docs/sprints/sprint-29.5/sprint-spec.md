# Sprint 29.5: Post-Session Operational Sweep

## Goal
Address all operational, safety, UI, and data-capture issues identified during the March 31, 2026 market session — the first full-day session with trailing stops active, 595 trades, and 12 strategies deployed. This sprint fixes critical flatten/zombie safety bugs, removes paper-trading data-capture blockers, corrects UI display bugs, improves real-time position updates, reduces log noise, adds MFE/MAE trade lifecycle tracking, and fixes the ORB Scalp structural shadow problem.

## Scope

### Deliverables

1. **Flatten/Zombie Safety Overhaul** — Root-cause fix for IBKR error 404 SELL order holds (re-query broker position qty before resubmit), global circuit breaker after retry exhaustion, EOD flatten covers broker-only positions, startup zombie flatten queued for market open, time-stop log suppression when flatten pending.

2. **Paper Trading Data-Capture Mode** — Disable weekly/daily loss limits and PerformanceThrottler suspension for paper trading to maximize signal and trade data collection.

3. **Win Rate Display Bug Fix + UI Improvements** — Fix win_rate proportion→percentage conversion, raise trades table row limit from 250 to 1000, add Shares column to Dashboard positions table, abbreviate Trailing Stop badge, increase trade stats polling frequency.

4. **Real-Time Position Updates via WebSocket** — Dashboard positions table consumes WS `position.updated` events for sub-second P&L updates instead of 5s REST polling.

5. **Log Noise Reduction** — Demote `ib_async.wrapper` validation warnings to DEBUG, rate-limit weekly loss rejection and reconciliation warnings, clean asyncio task shutdown.

6. **MFE/MAE Trade Lifecycle Tracking** — Track peak favorable/adverse excursion on every managed position tick, persist to trade records and debrief export for post-session optimal-exit analysis.

7. **ORB Scalp Exclusion Fix** — Add config flag to disable ORB family same-symbol mutual exclusion during paper trading, enabling ORB Scalp to generate independent signals.

### Acceptance Criteria

1. **Flatten/Zombie Safety:**
   - IBKR error 404 on SELL orders triggers broker position re-query and qty-corrected resubmit
   - After `max_flatten_retries` × `max_flatten_cycles` (new config, default 2 cycles), symbol added to `_flatten_abandoned` set; no further flatten attempts except EOD
   - `eod_flatten()` queries IBKR positions and submits SELL for any not in `_managed_positions`
   - `_flatten_unknown_position()` queues orders in `_startup_flatten_queue` when market is closed; queue drained on first CandleEvent after 9:30 ET
   - Time-stop INFO logs suppressed to 1 per 60s when `_flatten_pending` or `_flatten_abandoned` contains the symbol
   - Tests: ≥12 new tests covering error 404 handling, circuit breaker, EOD broker-only flatten, startup queue

2. **Paper Data-Capture Mode:**
   - `weekly_loss_limit_pct: 1.0` and `daily_loss_limit_pct: 1.0` in `config/risk_limits.yaml`
   - `throttler_suspend_enabled: false` added to `OrchestratorConfig` and `config/orchestrator.yaml`; when false, `PerformanceThrottler.evaluate()` returns `ThrottleAction.NONE` unconditionally
   - Tests: ≥3 new tests (throttler bypass, config validation)

3. **Win Rate + UI:**
   - `TradeStatsBar.tsx` passes `win_rate * 100` to `formatPercentRaw()`
   - Dashboard `TodayStatsCard` applies same multiplication + shows 1 decimal place
   - Backend `trades.py` `limit` param max raised from 250 to 1000
   - `TradesPage.tsx` requests `limit: 1000`
   - OpenPositions table includes Shares column (desktop/tablet only)
   - Exit reason label for `trailing_stop` → `"Trail"`
   - `useTradeStats.ts` polling interval reduced from 30s to 10s
   - Tests: ≥5 new Vitest tests

4. **Position WS Migration:**
   - New `usePositionUpdates()` hook subscribing to existing WS `position.updated` channel
   - Hook merges live P&L into `usePositions` query cache via `queryClient.setQueryData`
   - REST `usePositions` polling interval changed from 5s to 15s (consistency backstop)
   - Tests: ≥3 new Vitest tests

5. **Log Noise:**
   - `ib_async.wrapper` logger set to ERROR level; specific actionable codes (404, 202) logged at WARNING via Argus wrapper
   - Weekly loss limit rejection logged at WARNING max 1 per 60s via ThrottledLogger
   - Reconciliation mismatch consolidated to single WARNING per cycle
   - Shutdown sequence explicitly cancels known asyncio tasks and closes aiohttp sessions
   - Tests: ≥4 new tests

6. **MFE/MAE:**
   - `ManagedPosition` gains `mfe_price`, `mae_price`, `mfe_r`, `mae_r`, `mfe_time`, `mae_time` fields
   - On each tick in `_handle_position_tick()`, MFE/MAE updated when new extremes reached
   - Trade log record includes `mfe_r`, `mae_r`, `mfe_price`, `mae_price` columns
   - Debrief export includes MFE/MAE fields per trade
   - Tests: ≥8 new tests

7. **ORB Scalp Fix:**
   - `orb_family_mutual_exclusion` config flag in `orchestrator.yaml` (default `true`)
   - When `false`, `OrbBaseStrategy._check_breakout()` skips `_orb_family_triggered_symbols` check
   - Paper config sets `orb_family_mutual_exclusion: false`
   - Tests: ≥4 new tests

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `orchestrator.throttler_suspend_enabled` | `OrchestratorConfig` | `throttler_suspend_enabled` | `true` |
| `orchestrator.orb_family_mutual_exclusion` | `OrchestratorConfig` | `orb_family_mutual_exclusion` | `true` |
| `order_manager.max_flatten_cycles` | `OrderManagerConfig` | `max_flatten_cycles` | `2` |

Risk limit changes are value-only modifications to existing fields (no new Pydantic fields).

## Dependencies
- Sprint 29 complete and merged to `main` ✅
- IBKR paper trading active ✅
- Databento EQUS.MINI active ✅

## Relevant Decisions
- DEC-261: ORB family same-symbol exclusion (being made configurable)
- DEC-363: Flatten-pending guard (being extended with circuit breaker)
- DEC-369: Broker-confirmed positions never auto-closed (preserved — EOD flatten is explicit operator action)
- DEC-372: Stop resubmission cap (pattern extended to flatten cycles)
- DEC-375: Overflow routing (preserved, unmodified)

## Relevant Risks
- RSK-022: IB Gateway nightly resets — startup queue fix addresses pre-market zombie scenario

## Session Count Estimate
7 sessions estimated. S1 is the largest (14 compaction, safety-critical). S3/S4 are frontend sessions with visual review items (+0.5 contingency). S2 is trivially small (config-only). Total estimated: ~7.5 sessions including contingency.

## DEF Range
DEF-125 through DEF-135 reserved for this sprint.

## DEC Range
No new DECs expected — all changes follow established patterns. If novel decisions arise during implementation, DEC-382+ available.
