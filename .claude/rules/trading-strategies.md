# Trading Strategy Rules — ARGUS-Specific

> These rules apply to all ARGUS trading strategy development. See also: `backtesting.md` for validation/sweep rules.

## Strategy Architecture

- All strategies MUST be daily-stateful, session-stateless (DEC-028). State accumulates during market hours, resets between days, reconstructs from DB on mid-day restart.
- New strategies inherit from `BaseStrategy` unless they share a proven family base class (e.g., `OrbBaseStrategy` for ORB family). Do NOT extract shared base classes until 2+ strategies prove the abstraction is needed (DEC-152).
- Strategy spec sheets live at `docs/strategies/STRATEGY_{NAME}.md`. Auto-discovered by convention (DEC-181).
- Pipeline stage and family are config YAML properties, not derived from code (DEC-173/174).
- **Current roster:** see CLAUDE.md `## Current State` for the authoritative "N live + M shadow" count. Do not duplicate the roster here — it drifts.

## Risk and Execution

- Risk Manager NEVER modifies stop price or entry price. Only share count reduction and target tightening are allowed modifications (DEC-027).
- Concentration limit (5% single-stock) uses approve-with-modification — reduce shares to fit, reject if below 0.25R floor (DEC-249).
- Zero-R signals MUST be rejected upstream at the strategy level. If
  `entry == stop` (or within rounding noise) the SignalEvent must not be
  emitted. A minimum `risk_per_share` gate — plus an ATR-relative floor where
  applicable — belongs inside the strategy, not as a Risk Manager afterthought
  (DEC-251; DEF-152 Sprint 31.75 S1 lesson — gap_and_go emitted zero-R signals
  until the `min_risk_per_share=0.10` + 10%-of-ATR floor was added).
- All stock positions MUST close intraday. No overnight holds for stock strategies.
- Long only for V1. Short selling deferred (DEC-166, landed Sprint 28 as a decision — no short infrastructure implemented yet).
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
- **Fail-closed on missing reference data (DEC-277).** Semantic universe
  filters (`min_price`, `max_price`, `min_avg_volume`, `min_market_cap`) require
  the underlying reference value to evaluate. Absence of data is NOT a pass
  condition — symbols with `None` `prev_close` or `None` `avg_volume` are
  excluded at the `UniverseManager` gate, not silently admitted. Any new
  filter layer (e.g., experiment universe filter, sweep pre-filter) must
  inherit this posture.

## Regime Gating

- Every strategy declares `allowed_regimes: list[str]` in its YAML config
  (DEC-360 / Sprint 28.5).
- DEC-360 specifically added `bearish_trending` to the allowed-regimes list on
  all 7 legacy strategies to prevent dead sessions in down markets. New
  strategies MUST declare their allowed regimes explicitly — do not default to
  an empty list (which blocks everything) and do not rely on RegimeVector v2
  matching to permissively admit.
- Strategies that want regime-vector-aware gating read
  `RegimeOperatingConditions` submodel fields (VIX tier, vol-phase, term
  structure, VRP tier — Sprint 27.9) and match `None` as wildcard.

## PatternModule Conventions (Sprint 29 DEC-378; Sprints 31A.*–32.8)

New pattern-based strategies subclass
[argus/strategies/patterns/base.py](argus/strategies/patterns/base.py)
(`PatternModule` ABC) and wrap through `PatternBasedStrategy`. Conventions
that MUST be honored:

- **`get_default_params()` returns `list[PatternParam]`** — a frozen dataclass
  with eight fields (name, param_type, default, min_value, max_value, step,
  description, category). Grid builders (PatternBacktester,
  `build_parameter_grid`) introspect these; if the contract drifts the
  sweep infrastructure silently produces the wrong grid. DEC-378 codifies
  this.
- **Parameter-range consistency.** `PatternParam.min_value` / `max_value`
  must not be narrower than the Pydantic field's `ge` / `le` bounds on the
  pattern's config model. Sprint 32 found seven such discrepancies; a
  cross-validation test should accompany any new PatternModule.
- **Fingerprint = SHA-256 (first 16 hex) of canonical JSON (sorted keys,
  compact separators) of *detection params only*.** `strategy_id`, `name`,
  `enabled`, and `operating_window` are NOT in the fingerprint. See
  `argus/strategies/patterns/factory.py::compute_parameter_fingerprint`. The
  fingerprint is the identity key for the experiment registry — drift
  collapses variant dedup.
- **`lookback_bars` vs `min_detection_bars`.** `lookback_bars` is the deque
  *capacity*. `min_detection_bars` is the detection *eligibility window* —
  the minimum number of bars required before `detect()` may return a
  PatternDetection. Defaults to `lookback_bars` but patterns may override
  (DEF-147 pattern).
- **Build via factory at startup.** Use
  `build_pattern_from_config(pattern_name, config_dict)` in
  `argus/strategies/patterns/factory.py`. The factory reflects YAML
  parameters into the PatternModule constructor via PatternParam
  introspection. Do NOT instantiate patterns with no-argument constructors
  and then mutate attributes — that route was removed in Sprint 31A after
  DEF-143.

## Shadow Mode (StrategyMode, DEC-375, Sprint 27.7 / 27.95)

- `StrategyConfig.mode` accepts `"live"` (default) or `"shadow"`.
- Shadow strategies route around the quality pipeline and risk manager:
  `_process_signal()` in `main.py` recognizes shadow mode and hands the
  signal to the CounterfactualTracker instead of emitting an approved
  order. This lets a variant accumulate MAE/MFE/filter-accuracy data
  without touching real capital.
- Overflow routing (DEC-375) demotes live signals to shadow when the
  broker capacity (`overflow.broker_capacity`) is exhausted. Shadow fills
  are tracked identically; the signal does not disappear, it becomes
  counterfactual.
- Shadow demotion is also operator-driven — e.g., ABCD / Flat-Top
  demoted in Sprint 32.9 for optimization while still collecting data.

## Quality Pipeline Bypass

- When `SetupQualityEngine` is config-gated off
  (`quality_engine.enabled: false`) or the broker is
  `BrokerSource.SIMULATED`, `_process_signal()` falls back to legacy
  sizing: `allocated_capital * max_loss_per_trade_pct / risk_per_share`.
  This path is intentional and tested — do not remove it when editing
  the quality pipeline.

## BaseStrategy Telemetry Wire-Up (Sprints 24.5–25.6)

Every `BaseStrategy` implementation MUST emit `ENTRY_EVALUATION` events via
the ring buffer (`StrategyEvaluationBuffer`, `maxlen=1000`) with
`conditions_passed`/`conditions_total` metadata. These records flow to
`EvaluationEventStore` (data/evaluation.db, separate-DB pattern per DEC-345)
and drive the Observatory + Decision Stream UI. Since Sprint 31A this is
a mandatory convention — new strategies that skip it lose telemetry
visibility.

## Validation Requirements

- Walk-forward validation mandatory for all parameter optimization. WFE > 0.3 required (DEC-047).
- All pre-Databento backtests are PROVISIONAL — require re-validation with exchange-direct data (DEC-132). Do not treat Alpaca-era backtest results as production-grade.
- Cross-validation: VectorBT ↔ Replay Harness trade counts must be compared. VectorBT >= Replay = PASS (DEC-069).
- **Shadow-first validation (DEC-382, Sprint 31.75).** The current strategic
  posture is: deploy a small fleet of shadow variants,
  collect CounterfactualTracker data, promote by Pareto + hysteresis. This
  supersedes the "exhaustive VectorBT grid sweep before promotion" model.
  See `backtesting.md` for details.

## Config and Naming

- Strategy files: `snake_case.py` → class: `PascalCase` (e.g., `vwap_reclaim.py` → `VwapReclaimStrategy`)
- Config: `config/strategies/{strategy_name}.yaml` → Pydantic BaseModel validation (DEC-032)
- Strategy config includes: pipeline_stage, family, description_short, time_window_display, backtest_summary (DEC-172)

## Scanner

- All current strategies reuse the gap scanner (DEC-137/154). New strategies should reuse existing scanners when possible.
- Scanner must handle Databento historical data lag gracefully — retry with adjusted date range, fall back to static watchlist (DEC-247).
- Scanner simulation in backtests: compute gap from prev_close to day_open, apply scanner filters (DEC-052).
