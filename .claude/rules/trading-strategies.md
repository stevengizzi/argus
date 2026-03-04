# Trading Strategy Rules — ARGUS-Specific

> These rules apply to all ARGUS trading strategy development. See also: `backtesting.md` for VectorBT/sweep rules.

## Strategy Architecture

- All strategies MUST be daily-stateful, session-stateless (DEC-028). State accumulates during market hours, resets between days, reconstructs from DB on mid-day restart.
- New strategies inherit from `BaseStrategy` unless they share a proven family base class (e.g., `OrbBaseStrategy` for ORB family). Do NOT extract shared base classes until 2+ strategies prove the abstraction is needed (DEC-152).
- Strategy spec sheets live at `docs/strategies/STRATEGY_{NAME}.md`. Auto-discovered by convention (DEC-181).
- Pipeline stage and family are config YAML properties, not derived from code (DEC-173/174).

## Risk and Execution

- Risk Manager NEVER modifies stop price or entry price. Only share count reduction and target tightening are allowed modifications (DEC-027).
- Concentration limit (5% single-stock) uses approve-with-modification — reduce shares to fit, reject if below 0.25R floor (DEC-249).
- All stock positions MUST close intraday. No overnight holds for stock strategies.
- Long only for V1. Short selling deferred to Sprint 27 (DEC-166).
- Atomic bracket orders (entry + stop + T1 + T2) submitted together via `place_bracket_order()` (DEC-117). Never submit entry without protection.
- Per-signal time stops: `time_stop_seconds` on SignalEvent, carried to ManagedPosition (DEC-122). Strategy sets the value, Order Manager enforces it.

## Cross-Strategy Rules

- ALLOW_ALL duplicate stock policy (DEC-121/160). Multiple strategies can hold the same symbol simultaneously.
- 5% max single-stock exposure enforced ACROSS all strategies, not per-strategy.
- 15% max single-sector exposure (when sector data available — currently deferred, DEC-126).
- Circuit breakers are non-overridable. Daily loss limit 3–5%, weekly 5–8%.

## Data and Events

- Event Bus is the SOLE streaming mechanism (DEC-029). No callback subscriptions on DataService.
- CandleEvent routing: main.py subscribes to CandleEvent and routes to all active strategies via Orchestrator registry (DEC-125).
- Databento callbacks arrive on reader thread — bridge to asyncio via `call_soon_threadsafe()` (DEC-088).
- EQUS.MINI is the production dataset (DEC-248). Covers all US exchanges in one feed.
- Databento prices are fixed-point format scaled by 1e9 (DEC-243). Always divide.

## Validation Requirements

- Walk-forward validation mandatory for all parameter optimization. WFE > 0.3 required (DEC-047).
- All pre-Databento backtests are PROVISIONAL — require re-validation with exchange-direct data (DEC-132). Do not treat Alpaca-era backtest results as production-grade.
- Cross-validation: VectorBT ↔ Replay Harness trade counts must be compared. VectorBT >= Replay = PASS (DEC-069).
- VectorBT sweeps MUST use precompute+vectorize architecture (DEC-149). See `backtesting.md` for details.

## Config and Naming

- Strategy files: `snake_case.py` → class: `PascalCase` (e.g., `vwap_reclaim.py` → `VwapReclaimStrategy`)
- Config: `config/strategies/{strategy_name}.yaml` → Pydantic BaseModel validation (DEC-032)
- Strategy config includes: pipeline_stage, family, description_short, time_window_display, backtest_summary (DEC-172)

## Scanner

- All current strategies reuse the gap scanner (DEC-137/154). New strategies should reuse existing scanners when possible.
- Scanner must handle Databento historical data lag gracefully — retry with adjusted date range, fall back to static watchlist (DEC-247).
- Scanner simulation in backtests: compute gap from prev_close to day_open, apply scanner filters (DEC-052).
