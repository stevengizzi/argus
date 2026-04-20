# Sprint 28.5 Design Summary

**Sprint Goal:** Deliver configurable, per-strategy exit management to the Order Manager, BacktestEngine, and CounterfactualTracker — trailing stops (ATR/percent/fixed), partial profit-taking with trail on remainder after T1, and time-based exit escalation (progressive stop tightening as hold time increases).

**Execution Mode:** Human-in-the-loop

**Adversarial Review:** Yes — Order Manager is safety-critical; fill model changes affect all backtesting validation.

---

**Session Breakdown:**

- **S1:** Exit math pure functions — shared stateless computation for trailing stop price, escalation stop price, and effective stop (max of all sources). Pattern: same role as `core/fill_model.py`.
  - Creates: `argus/core/exit_math.py`
  - Modifies: —
  - Integrates: N/A (foundation)
  - Score: 9 (Medium)
  - Tests: ~12

- **S2:** Config models + SignalEvent `atr_value` field — Pydantic models for exit management config, new `exit_management.yaml`, add `atr_value: float | None = None` to SignalEvent and SignalRejectedEvent.
  - Creates: `config/exit_management.yaml`
  - Modifies: `argus/core/config.py`, `argus/core/events.py`
  - Integrates: S1 (type references from exit_math)
  - Score: 13 (Medium)
  - Tests: ~10

- **S3:** Strategy ATR emission + main.py config loading — all 7 strategies emit `atr_value` on SignalEvent; main.py loads exit_management.yaml and passes ExitManagementConfig to Order Manager.
  - Creates: —
  - Modifies: 7 strategy files (mechanical: add `atr_value=` to signal constructor), `argus/main.py`
  - Integrates: S2 (atr_value field on SignalEvent, ExitManagementConfig)
  - Score: 8 (Low)
  - Tests: ~6

- **S4a:** Order Manager — exit config loading + position trail state fields — add ExitManagementConfig reference to OrderManager, per-strategy config lookup method, extend ManagedPosition with trail state fields (`trail_active`, `trail_stop_price`, `escalation_phase`).
  - Creates: —
  - Modifies: `argus/execution/order_manager.py`
  - Integrates: S2 (config models), S3 (config passed from main.py)
  - Score: 9 (Medium)
  - Tests: ~6

- **S4b:** Order Manager — trailing stop + escalation logic — upgrade `on_tick()` to use exit_math for trail computation, modify `_handle_t1_fill()` to activate trail, add escalation checks to fallback poll loop, belt-and-suspenders pattern (server trail + broker safety stop at breakeven).
  - Creates: —
  - Modifies: `argus/execution/order_manager.py`
  - Integrates: S1 (exit_math functions), S4a (config + position fields)
  - Score: 13 (Medium)
  - Tests: ~12

- **S5:** BacktestEngine + CounterfactualTracker alignment — add trail/escalation state to BacktestPosition and ShadowPosition, call exit_math per bar to update effective stop, pass updated stop to existing fill model. Verify existing non-trail behavior is identical.
  - Creates: —
  - Modifies: `argus/backtest/engine.py`, `argus/intelligence/counterfactual.py`
  - Integrates: S1 (exit_math), S2 (config)
  - Score: 13 (Medium)
  - Tests: ~12

- **S5f:** Batch fix contingency — 0.5 session budget for review findings.

**Total: 6 sessions + 1 contingency. ~58–68 estimated new tests.**

**Dependency chain:** S1 → S2 → S3 → S4a → S4b → S5

---

**Key Decisions:**

1. **Regime-adaptive targets deferred to Sprint 32+.** Sprint 28.5 builds mechanical exit infrastructure that accepts parameters which _could_ be regime-driven later. Mechanism first, policy second — Learning Loop needs data before we guess at regime adjustments.

2. **ATR passed on SignalEvent (`atr_value: float | None`).** Strategies already compute ATR. No new coupling into Order Manager. Backtest/counterfactual compatible (ATR travels with signal). Fallback: if atr_value is None, trail uses percent-based mode.

3. **Server-side trailing stops (not IBKR native trailing orders).** Order Manager tracks trail internally, flattens via market sell when triggered. Avoids IBKR amendment churn (DEC-372/373 lessons). Enables progressive tightening (impossible with broker-side trails). Latency negligible for 5–60 min holds.

4. **Belt-and-suspenders pattern.** After T1 fill: broker safety stop remains at breakeven (crash protection), server-side trail operates above it. If trail triggers → cancel broker stop → flatten. If server crashes → broker stop protects at breakeven.

5. **TheoreticalFillModel stays stateless.** Shared pure functions in new `exit_math.py` compute trail/escalation stop prices. BacktestEngine and CounterfactualTracker manage trail state on their position objects, pass updated stops to `evaluate_bar_exit()` each bar. No new statefulness in fill model.

6. **Per-strategy exit config with global defaults.** `exit_management.yaml` defines global defaults. Each strategy YAML can override under `exit_management:` key. Strategies opt-in to trailing/escalation — default is `enabled: false` everywhere.

7. **Trailing stop activation after T1 fill (default).** Configurable: `"after_t1"` (default), `"after_profit_pct"`, `"immediate"`. ORB Scalp and similar fast strategies keep `trailing_stop.enabled: false`.

8. **Escalation defined relative to time_stop.** Phases expressed as `elapsed_pct` of `time_stop_seconds`. If signal has no time_stop, escalation is inactive. Hard `max_position_duration_minutes` still applies as safety net.

---

**Scope Boundaries:**

- **IN:** Trailing stop engine (ATR/percent/fixed, per-strategy config), partial profit-taking with trail on T1 remainder, time-based exit escalation (progressive stop tightening), BacktestEngine + CounterfactualTracker alignment, `atr_value` on SignalEvent
- **OUT:** Regime-adaptive exit parameters (Sprint 32+), new ExitReason enum values (TRAILING_STOP already exists), Risk Manager exit behavior changes (DEC-027), short selling exit logic (Sprint 30), frontend changes, new API endpoints, T1/T2 split ratio changes, multi-leg partial exits (T1/T2/T3), broker-side trailing stop orders, behavioral changes for non-opt-in strategies

---

**Regression Invariants:**

1. Strategies without exit management config → identical behavior (no trail, no escalation)
2. T1/T2 bracket flow unchanged for non-trail strategies
3. Risk Manager never touches exits (DEC-027)
4. BacktestEngine produces identical results for strategies without exit config
5. CounterfactualTracker produces identical results for non-trail shadow positions
6. ExitReason values logged correctly (TRAILING_STOP for trail, TIME_STOP for escalation)
7. IBKR bracket safety stop still placed at breakeven after T1 (belt-and-suspenders)
8. EOD flatten unconditional at 15:50 ET
9. Overflow routing (DEC-375) unaffected
10. SignalEvent backward compatible (`atr_value=None` default)

---

**File Scope:**

- **Create:**
  - `argus/core/exit_math.py`
  - `config/exit_management.yaml`

- **Modify:**
  - `argus/core/events.py` (add atr_value to SignalEvent + SignalRejectedEvent)
  - `argus/core/config.py` (add TrailingStopConfig, EscalationPhase, ExitEscalationConfig, ExitManagementConfig)
  - `argus/execution/order_manager.py` (trailing stop upgrade, escalation, config loading, position fields)
  - `argus/backtest/engine.py` (trail/escalation state per position, exit_math integration)
  - `argus/intelligence/counterfactual.py` (trail/escalation state per shadow position, exit_math integration)
  - `argus/main.py` (load exit_management.yaml, pass config to OrderManager)
  - 7 strategy files (mechanical: add atr_value to signal emissions)

- **Do not modify:**
  - `argus/core/fill_model.py` (stays stateless, unchanged)
  - `argus/core/risk_manager.py` (DEC-027: RM never modifies stops)
  - `argus/intelligence/learning/` (Learning Loop unchanged — will consume new exit data naturally)
  - `argus/ui/` (no frontend work)
  - `argus/api/` (no new endpoints)
  - `argus/ai/` (AI layer unchanged)
  - `config/risk_limits.yaml`
  - `config/order_manager.yaml` (existing fields preserved; new exit config in separate file)

---

**Config Changes:**

New file `config/exit_management.yaml`:

| YAML Path | Pydantic Field | Type | Default |
|-----------|---------------|------|---------|
| `trailing_stop.enabled` | `TrailingStopConfig.enabled` | `bool` | `false` |
| `trailing_stop.type` | `TrailingStopConfig.type` | `Literal["atr","percent","fixed"]` | `"atr"` |
| `trailing_stop.atr_multiplier` | `TrailingStopConfig.atr_multiplier` | `float` (gt=0) | `2.5` |
| `trailing_stop.percent` | `TrailingStopConfig.percent` | `float` (gt=0, le=0.2) | `0.02` |
| `trailing_stop.fixed_distance` | `TrailingStopConfig.fixed_distance` | `float` (gt=0) | `0.50` |
| `trailing_stop.activation` | `TrailingStopConfig.activation` | `Literal["after_t1","after_profit_pct","immediate"]` | `"after_t1"` |
| `trailing_stop.activation_profit_pct` | `TrailingStopConfig.activation_profit_pct` | `float` (ge=0) | `0.005` |
| `trailing_stop.min_trail_distance` | `TrailingStopConfig.min_trail_distance` | `float` (ge=0) | `0.05` |
| `escalation.enabled` | `ExitEscalationConfig.enabled` | `bool` | `false` |
| `escalation.phases` | `ExitEscalationConfig.phases` | `list[EscalationPhase]` | `[]` |
| `escalation.phases[].elapsed_pct` | `EscalationPhase.elapsed_pct` | `float` (gt=0, le=1) | — |
| `escalation.phases[].stop_to` | `EscalationPhase.stop_to` | `Literal["breakeven","half_profit","full_profit"]` | — |

Per-strategy override: `exit_management:` key in strategy YAMLs, same structure, merged over global defaults.

New field on SignalEvent / SignalRejectedEvent:

| Field | Type | Default |
|-------|------|---------|
| `atr_value` | `float \| None` | `None` |

Regression checklist item: "All keys in `exit_management.yaml` verified against Pydantic model — no silently ignored fields."

---

**Test Strategy:**

- S1: ~12 tests — pure function coverage for `compute_trailing_stop()`, `compute_escalation_stop()`, `compute_effective_stop()` across all trail types, edge cases (None ATR, zero distance, phase boundaries)
- S2: ~10 tests — Pydantic model validation (invalid types, boundary values, defaults), config loading, atr_value on SignalEvent
- S3: ~6 tests — ATR propagation through 2–3 representative strategies, main.py config loading
- S4a: ~6 tests — Order Manager config lookup, ManagedPosition field initialization
- S4b: ~12 tests — trailing stop activation on T1, trail price updates on tick, escalation phase transitions, belt-and-suspenders (trail + broker stop coexistence), non-trail strategy unchanged behavior
- S5: ~12 tests — BacktestEngine trail state per bar, CounterfactualTracker trail state, existing non-trail behavior unchanged
- **Total: ~58–68 new tests**
- Full suite run at S1 pre-flight and S5 close-out. Scoped tests for mid-sprint sessions.

---

**Runner Compatibility:**

- Mode: Human-in-the-loop
- Parallelizable sessions: None (linear dependency chain)
- Runner config: Not generated (HITL mode)

---

**Dependencies:**

- Sprint 28 complete (Learning Loop V1) ✅
- All 8 pre-existing pytest failures resolved ✅ (post-sprint triage)
- IntradayCandleStore operational (Sprint 27.65) ✅
- CounterfactualTracker operational (Sprint 27.7) ✅
- BacktestEngine operational (Sprint 27) ✅

---

**Escalation Criteria:**

- Any change to `_handle_t1_fill()` control flow that could cause position leak (shares not tracked)
- Any change that silently alters behavior for strategies with `trailing_stop.enabled: false`
- BacktestEngine producing different results for existing strategy configs (regression)
- IBKR bracket order interaction failures during trail activation
- Trail + escalation + time_stop + EOD flatten priority conflicts

---

**Doc Updates Needed:**

- `docs/project-knowledge.md` — Exit Management section, updated OrderManager description, updated ExitReason usage, Sprint 28.5 in sprint history
- `docs/architecture.md` — Exit management subsection, exit_math.py, config changes
- `docs/decision-log.md` — New DECs (reserve DEC-378–385)
- `docs/sprint-history.md` — Sprint 28.5 entry
- `docs/roadmap.md` — Mark Sprint 28.5 complete, update Phase 6 Gate description
- `CLAUDE.md` — Update next sprint, config file list, exit management notes
- `docs/pre-live-transition-checklist.md` — Exit management config values to review before live

---

**Artifacts to Generate:**

1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with Creates/Modifies/Integrates/Score per session)
4. Sprint-Level Escalation Criteria
5. Sprint-Level Regression Checklist
6. Doc Update Checklist
7. Adversarial Review Input Package
8. Review Context File
9. Implementation Prompts ×6 (S1, S2, S3, S4a, S4b, S5)
10. Tier 2 Review Prompts ×6
11. Work Journal Handoff Prompt
