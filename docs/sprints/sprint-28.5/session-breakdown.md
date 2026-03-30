# Sprint 28.5: Session Breakdown

> **Revision:** Post-adversarial review (March 29, 2026). Amendment references added to affected sessions.

**Dependency chain:** S1 → S2 → S3 → S4a → S4b → S5 → (S5f contingency)

**Execution mode:** Human-in-the-loop

---

## Session S1: Exit Math Pure Functions

**Objective:** Create `argus/core/exit_math.py` — shared stateless computation library for trailing stop price, escalation stop price, and effective stop selection. Include AMD-5 `stop_to` formulas (all profit-based values reference `high_watermark`) and AMD-12 negative/zero ATR guard.

**Creates:**
- `argus/core/exit_math.py`
- `tests/unit/core/test_exit_math.py`

**Modifies:** —

**Integrates:** N/A (foundation session)

**Parallelizable:** false (foundation for all subsequent sessions)

**Amendments:** AMD-5 (`stop_to` enum definitions and formulas), AMD-12 (negative/zero ATR guard)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (exit_math.py) | 2 |
| Files modified | 0 | 0 |
| Context reads | 1 (fill_model.py for pattern reference) | 1 |
| New tests | ~14 | 7 |
| Complex integration | 0 | 0 |
| External API debug | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **10 (Medium)** |

**Tests (~14):**
- `compute_trailing_stop()` — ATR type with valid ATR
- `compute_trailing_stop()` — percent type
- `compute_trailing_stop()` — fixed type
- `compute_trailing_stop()` — ATR type with None ATR (returns None or falls back to percent)
- `compute_trailing_stop()` — ATR type with negative ATR → returns None (AMD-12)
- `compute_trailing_stop()` — ATR type with zero ATR → returns None (AMD-12)
- `compute_trailing_stop()` — min_trail_distance floor enforced
- `compute_trailing_stop()` — disabled config returns None
- `compute_escalation_stop()` — breakeven phase (AMD-5 formula)
- `compute_escalation_stop()` — quarter_profit phase (AMD-5 formula, uses high_watermark)
- `compute_escalation_stop()` — half_profit phase (AMD-5 formula)
- `compute_escalation_stop()` — three_quarter_profit phase (AMD-5 formula)
- `compute_escalation_stop()` — no time_stop (returns None)
- `compute_effective_stop()` — takes max of all non-None stop sources

---

## Session S2: Config Models + SignalEvent atr_value

**Objective:** Create Pydantic config models for exit management with field-level deep merge (AMD-1), create `exit_management.yaml`, add `atr_value` field to SignalEvent and SignalRejectedEvent. Include deprecated config warning (AMD-10).

**Creates:**
- `config/exit_management.yaml`
- `tests/unit/core/test_exit_management_config.py`

**Modifies:**
- `argus/core/config.py` (add TrailingStopConfig, EscalationPhase, ExitEscalationConfig, ExitManagementConfig, `deep_update()` utility, `StopToLevel` string enum with AMD-5 values)
- `argus/core/events.py` (add `atr_value: float | None = None` to SignalEvent and SignalRejectedEvent)

**Integrates:** S1 (exit_math type references in config validation)

**Parallelizable:** false

**Amendments:** AMD-1 (field-level deep merge), AMD-5 (`StopToLevel` enum), AMD-10 (deprecated config warning), AMD-11 (`min_trail_distance` note)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (exit_management.yaml) | 2 |
| Files modified | 2 (config.py, events.py) | 2 |
| Context reads | 4 (config.py, events.py, exit_math.py, order_manager.yaml) | 4 |
| New tests | ~12 | 6 |
| Complex integration | 0 | 0 |
| External API debug | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **14** |

Score hits 14 (High threshold). The additional tests from AMD-1 (deep merge) and AMD-10 (deprecated warning) push this up. Acceptable because the complexity is in config model tests (low risk), not integration wiring. If implementer feels pressure, the deprecated warning test can defer to S3.

**Tests (~12):**
- TrailingStopConfig valid defaults
- TrailingStopConfig validation (atr_multiplier ≤ 0 rejected, percent > 0.2 rejected)
- EscalationPhase validation (elapsed_pct > 1.0 rejected)
- StopToLevel enum has all 4 AMD-5 values
- ExitEscalationConfig phases sorting validation
- ExitManagementConfig round-trip from YAML
- Config loading from `exit_management.yaml` file
- Unknown key in YAML detected (Pydantic extra="forbid" or similar)
- **Field-level deep merge (AMD-1):** strategy override of single field inherits remaining from global
- **Deep merge edge case:** strategy override of entire trailing_stop section
- SignalEvent with atr_value=None (backward compat)
- SignalEvent with atr_value=1.5 (set correctly)

---

## Session S3: Strategy ATR Emission + main.py Config Loading

**Objective:** Wire all 7 strategies to emit `atr_value` on SignalEvent using ATR(14) via IndicatorEngine (AMD-9). Load `exit_management.yaml` in main.py and pass ExitManagementConfig to Order Manager constructor. Log deprecated config warning if legacy fields active (AMD-10).

**Creates:**
- `tests/unit/strategies/test_atr_emission.py`

**Modifies:**
- `argus/strategies/orb_breakout.py` (add atr_value to signal emission + ATR source comment)
- `argus/strategies/orb_scalp.py` (add atr_value to signal emission + ATR source comment)
- `argus/strategies/vwap_reclaim.py` (add atr_value to signal emission + ATR source comment)
- `argus/strategies/afternoon_momentum.py` (add atr_value to signal emission + ATR source comment)
- `argus/strategies/red_to_green.py` (add atr_value to signal emission + ATR source comment)
- `argus/strategies/pattern_strategy.py` (add atr_value to signal emission — may be None if no IndicatorEngine ATR + ATR source comment)
- `argus/main.py` (load exit_management.yaml, pass config to OrderManager, deprecated config check)

**Integrates:** S2 (atr_value field on SignalEvent, ExitManagementConfig Pydantic model)

**Parallelizable:** false

**Amendments:** AMD-9 (ATR(14) standardization, document ATR source in code comments), AMD-10 (startup deprecated config warning in main.py)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 (main.py + pattern_strategy.py as representative; remaining 5 strategies are mechanical single-line additions) | 2 |
| Context reads | 4 (events.py, 2 strategy files, exit_management.yaml) | 4 |
| New tests | ~6 | 3 |
| Complex integration | 0 | 0 |
| External API debug | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **9** |

**Tests (~6):**
- ORB Breakout emits non-None atr_value on signal (ATR(14) via IndicatorEngine)
- VWAP Reclaim emits non-None atr_value on signal
- PatternBasedStrategy (Bull Flag) emits atr_value (None if no IndicatorEngine ATR access)
- main.py loads exit_management.yaml without error
- main.py passes ExitManagementConfig to OrderManager constructor
- Deprecated config warning logged when legacy `enable_trailing_stop: true`

---

## Session S4a: Order Manager — Exit Config + Position Trail State

**Objective:** Add ExitManagementConfig to OrderManager, implement per-strategy config lookup with field-level deep merge, and extend ManagedPosition with trail/escalation state fields.

**Creates:** —

**Modifies:**
- `argus/execution/order_manager.py` (constructor accepts ExitManagementConfig, per-strategy config lookup method, ManagedPosition new fields)

**Integrates:** S2 (ExitManagementConfig), S3 (config passed from main.py)

**Parallelizable:** false

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 1 (order_manager.py) | 1 |
| Context reads | 3 (order_manager.py position class + init, config.py, exit_management.yaml) | 3 |
| New tests | ~6 | 3 |
| Complex integration | 0 | 0 |
| External API debug | 0 | 0 |
| Large files (>150 lines) | 2 (order_manager.py is ~1800 lines) | 2 |
| **Total** | | **9 (Medium)** |

**ManagedPosition new fields:**
- `trail_active: bool = False`
- `trail_stop_price: float = 0.0`
- `escalation_phase_index: int = -1` (index into phases list; -1 = no phase reached)
- `exit_config: ExitManagementConfig | None = None` (per-strategy resolved config)
- `atr_value: float | None = None` (captured from signal)

**Tests (~6):**
- OrderManager accepts ExitManagementConfig in constructor
- Per-strategy config lookup returns strategy-specific override (field-level deep merge)
- Per-strategy config lookup returns global default when no override
- ManagedPosition initializes with trail_active=False
- ManagedPosition captures atr_value from signal
- ManagedPosition captures exit_config from per-strategy lookup

---

## Session S4b: Order Manager — Trailing Stop + Escalation Logic

**Objective:** Upgrade `on_tick()` trailing stop logic to use exit_math, modify `_handle_t1_fill()` to activate trail, add escalation checks to fallback poll loop. Implement AMD-2 flatten order-of-operations (sell first, cancel second), AMD-3 escalation failure recovery, AMD-4 shares_remaining guard, AMD-6 escalation exempt from retry cap, AMD-8 flatten_pending check first.

**Creates:**
- `tests/unit/execution/test_order_manager_exit_management.py`

**Modifies:**
- `argus/execution/order_manager.py` (on_tick trailing logic, _handle_t1_fill trail activation, fallback poll escalation, flatten order-of-operations)

**Integrates:** S1 (exit_math functions), S4a (config reference + position fields)

**Parallelizable:** false

**Amendments:** AMD-2 (flatten order-of-operations), AMD-3 (escalation failure recovery), AMD-4 (shares_remaining guard), AMD-6 (escalation exempt from retry cap), AMD-8 (flatten_pending check first)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 1 (order_manager.py) | 1 |
| Context reads | 3 (order_manager.py on_tick + handle_t1 + flatten, exit_math.py, config models) | 3 |
| New tests | ~15 | 7.5 |
| Complex integration | 3 (wiring exit_math + config + existing OM state machine) | 3 |
| External API debug | 0 | 0 |
| Large files (>150 lines) | 0 (already counted in S4a context) | 0 |
| **Total** | | **14.5** |

Score hits 14.5 (High). The safety-critical amendments (AMD-2/3/4/6/8) add required tests. This session is inherently complex — it's the core Order Manager state machine change. Acceptable because: (a) no new files created, (b) single file modified, (c) the additional tests are guards/recovery paths not new features. If implementer feels pressure, AMD-3 recovery path testing can overflow to S5f.

**Tests (~15):**
- Trail activates on T1 fill when trailing_stop.enabled=true
- Trail does NOT activate on T1 fill when trailing_stop.enabled=false
- Trail price updates on tick (high watermark increases → trail ratchets up)
- Trail price does not decrease (only ratchets up)
- Position flattens when price ≤ trail stop
- **AMD-2:** Flatten order is sell first, cancel safety stop second
- **AMD-4:** Trail flatten skipped when shares_remaining == 0
- **AMD-8:** Trail flatten is no-op when _flatten_pending already set for symbol
- Escalation phase triggers at correct elapsed_pct threshold
- Escalation adjusts broker stop order (cancel old, submit new)
- **AMD-3:** Escalation stop resubmission failure → flatten attempt
- **AMD-6:** Escalation stop update does not increment stop_cancel_retry count
- Effective stop = max(original, trail, escalation)
- Strategy with no exit config → identical behavior to pre-sprint
- activation="after_profit_pct" — trail activates only after profit threshold

---

## Session S5: BacktestEngine + CounterfactualTracker Alignment

**Objective:** Add trail/escalation state to BacktestPosition and ShadowPosition. Implement AMD-7 bar-processing order (prior state for exit check, THEN update state). Verify non-trail strategies produce identical results.

**Creates:**
- `tests/unit/backtest/test_engine_exit_management.py`
- `tests/unit/intelligence/test_counterfactual_exit_management.py`

**Modifies:**
- `argus/backtest/engine.py` (BacktestPosition trail state, per-bar trail/escalation update with AMD-7 ordering, effective stop computation)
- `argus/intelligence/counterfactual.py` (ShadowPosition trail state, per-bar trail/escalation update with AMD-7 ordering)

**Integrates:** S1 (exit_math), S2 (ExitManagementConfig)

**Parallelizable:** false

**Amendments:** AMD-7 (bar-processing order: prior state → evaluate → update)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 (engine.py, counterfactual.py) | 2 |
| Context reads | 5 (engine.py, counterfactual.py, exit_math.py, fill_model.py, config.py) | 5 |
| New tests | ~13 | 6.5 |
| Complex integration | 0 (using pure functions, no multi-component wiring) | 0 |
| External API debug | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **13.5 (Medium)** |

**Tests (~13):**
- BacktestEngine: trail state updates per bar (high watermark from bar.high)
- BacktestEngine: trail-triggered exit at correct price
- BacktestEngine: escalation phase triggers at correct bar
- BacktestEngine: effective stop = max(original, trail, escalation)
- BacktestEngine: non-trail strategy produces identical results to pre-sprint (regression)
- BacktestEngine: trail + time_stop interaction (time stop still fires if trail hasn't)
- **AMD-7:** BacktestEngine bar-processing order test: bar high=$52, low=$49, prior trail=$49.50, updated trail=$50.50 → exit at $49.50 (prior state)
- CounterfactualTracker: trail state updates per bar
- CounterfactualTracker: trail-triggered exit at correct price
- CounterfactualTracker: escalation phase triggers at correct bar
- CounterfactualTracker: non-trail shadow position identical to pre-sprint (regression)
- CounterfactualTracker: backfill bars update trail state correctly
- CounterfactualTracker: trail triggers during backfill → position closes

---

## Session S5f: Batch Fix Contingency

**Objective:** Address any findings from S5 review or accumulated issues across the sprint.

**Creates:** TBD (based on findings)
**Modifies:** TBD
**Integrates:** TBD

Contingency session — 0.5 session budget. Used only if reviews surface issues.

---

## Summary

| Session | Scope | Creates | Modifies | Score | Tests | Key Amendments |
|---------|-------|---------|----------|-------|-------|----------------|
| S1 | Exit math pure functions | exit_math.py | — | 10 (Med) | ~14 | AMD-5, AMD-12 |
| S2 | Config models + SignalEvent atr_value | exit_management.yaml | config.py, events.py | 14 (High*) | ~12 | AMD-1, AMD-5, AMD-10, AMD-11 |
| S3 | Strategy ATR emission + main.py | — | 7 strategies, main.py | 9 (Med) | ~6 | AMD-9, AMD-10 |
| S4a | OM exit config + position fields | — | order_manager.py | 9 (Med) | ~6 | — |
| S4b | OM trailing stop + escalation logic | — | order_manager.py | 14.5 (High*) | ~15 | AMD-2, AMD-3, AMD-4, AMD-6, AMD-8 |
| S5 | BacktestEngine + CounterfactualTracker | — | engine.py, counterfactual.py | 13.5 (Med) | ~13 | AMD-7 |
| S5f | Batch fix contingency | TBD | TBD | — | — | — |
| **Total** | | | | | **~66** | |

*S2 and S4b score at the High threshold (14/14.5). Both are accepted because: S2's complexity is in config model tests (low risk); S4b is inherently the core state machine change and further splitting would fragment the safety-critical logic across sessions, increasing integration risk. If either session encounters compaction pressure, overflow to S5f.
