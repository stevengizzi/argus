# Sprint 28.5: What This Sprint Does NOT Do

> **Revision:** Post-adversarial review (March 29, 2026). AMD-10, AMD-11 incorporated.

## Out of Scope

1. **Regime-adaptive exit parameters:** Exit targets, trail distances, and escalation schedules are static per-strategy config values. Dynamic adjustment based on current RegimeVector is deferred to Sprint 32+ when the Learning Loop has accumulated enough data to inform regime-specific policies. The infrastructure built here _accepts_ parameters that could later be regime-driven, but the mapping from regime → parameters is not part of this sprint.

2. **New ExitReason enum values:** `ExitReason.TRAILING_STOP` already exists in `core/events.py`. Escalation-triggered stops use the existing `TRAILING_STOP` or `TIME_STOP` reasons depending on what triggered the exit. No new enum values needed.

3. **Short selling exit logic:** All exit math assumes long positions (trail stop below high watermark, escalation tightens upward). Short selling infrastructure is Sprint 30. Exit math functions should be designed so short-side logic can be added later (e.g., a `side` parameter), but the implementation only handles longs.

4. **Frontend changes:** No new UI components, panels, or pages. The existing Trade Log, Performance, and Debrief pages already display ExitReason values — TRAILING_STOP exits will surface automatically through existing rendering.

5. **New API endpoints:** No new REST or WebSocket endpoints. The existing `/api/v1/trades`, `/api/v1/positions`, and position WebSocket already expose exit reasons and P&L data.

6. **Multi-leg partial exits (T1/T2/T3):** The current T1/T2 two-target system is preserved. Adding a third partial exit level is not in scope. The T1→trail pattern replaces the need for T2 in trail-enabled strategies (T2 becomes a soft ceiling, not a separate partial exit).

7. **Broker-side trailing stop orders:** IBKR native trailing stops are not used. All trailing is server-side in the Order Manager. This avoids IBKR amendment churn and enables progressive tightening.

8. **T1/T2 share split ratio changes:** `t1_position_pct` remains configurable via `order_manager.yaml` (default 0.5). This sprint does not change how shares are split between T1 and T2.

9. **Learning Loop exit-specific analysis:** The Learning Loop (Sprint 28) will naturally observe trailing stop outcomes through its existing OutcomeCollector. No Learning Loop code changes are needed to consume the new exit data. Exit-specific analysis (e.g., "did trailing stop improve expectancy?") is deferred to Learning Loop V2 (Sprint 40).

10. **Trailing stop on the full position (pre-T1):** With `activation: "after_t1"` (default), the trail only activates after T1 fills. We do not implement trailing the full position before T1 in this sprint — the `"immediate"` activation option activates trail logic at entry but T1/T2 bracket orders still control the initial exit flow. The interaction between "immediate" trail and active T1/T2 bracket orders is intentionally simple: trail only triggers flatten for shares not already covered by pending bracket orders.

11. **Percentage-based `min_trail_distance` (AMD-11):** The default `min_trail_distance: 0.05` ($0.05) is a fixed-dollar floor, calibrated for the $5–$200 price range typical of ARGUS universe filters. A future enhancement could express this as a percentage floor, but the fixed-dollar V1 is sufficient given current universe constraints. Per-strategy override is available for stocks outside this range.

## Edge Cases to Reject

1. **ATR value changes after signal emission:** ATR is captured at signal time and does not update during the position's lifetime. For day trading holds of 5–60 minutes, ATR drift is negligible. Do NOT implement real-time ATR updates in the Order Manager.

2. **Trail stop tighter than original stop:** If the computed trail stop is below the original stop (e.g., for a newly opened position), the effective stop is the original stop. The trail only ratchets upward from the original stop, never below it. `compute_effective_stop()` handles this via max().

3. **Escalation with no phases configured:** `escalation.enabled: true` but `phases: []` → escalation is effectively a no-op. Log a WARNING at config load time but do not raise an error. This is a valid (if pointless) configuration.

4. **Multiple escalation phases triggering simultaneously:** If a position has been open long enough that it's past two phase boundaries at the first check, apply only the latest (most aggressive) phase. Phases are ordered by `elapsed_pct` ascending; the latest triggered phase wins.

5. **Trail activation during backfill:** When CounterfactualTracker backfills bars from IntradayCandleStore at shadow position open, trail state should update through backfill bars normally. If trail triggers during backfill, the position closes at the trail price on that bar. This is correct behavior — the signal was rejected, and the theoretical position would have been stopped out.

6. **Strategy with trailing stop but no T2 target:** Valid configuration. After T1 fills and trail activates, the trail is the only exit mechanism (besides time stop, escalation, and EOD flatten). No T2 order is submitted. This is already handled by the existing `t2_price > 0` guard.

7. **Odd-lot trail exits:** Trail-triggered flatten of 1–2 remaining shares may get odd-lot treatment from IBKR. This is not a new concern (already true for T2 exits) and does not require special handling.

8. **Negative or zero ATR (AMD-12):** A strategy emitting `atr_value <= 0` or `atr_value = None` with ATR trail type selected → `compute_trailing_stop()` returns None. Trail falls back to percent-based if configured, otherwise no trail. Never produces a trail price from invalid ATR.

## Scope Boundaries

- **Do NOT modify:**
  - `argus/core/fill_model.py` — stays stateless and unchanged. New exit logic lives in `exit_math.py`.
  - `argus/core/risk_manager.py` — RM never modifies stops (DEC-027). Exit management is exclusively Order Manager's responsibility.
  - `argus/intelligence/learning/` — Learning Loop unchanged. Will consume new exit data naturally.
  - `argus/ui/` — no frontend modifications.
  - `argus/api/routes/` — no new or modified API endpoints.
  - `argus/ai/` — AI layer unchanged.
  - `config/risk_limits.yaml` — risk limits unchanged.
  - `config/order_manager.yaml` — existing fields preserved. New exit config in separate file.
  - `argus/data/` — no data service changes.
  - `argus/analytics/` — no analytics changes (trade logger already handles all ExitReason values).

- **Do NOT optimize:**
  - Trail price computation is simple arithmetic — no need for caching, vectorization, or precomputation.
  - Config merging (global + per-strategy) happens at startup. No need for runtime config hot-reload.

- **Do NOT refactor:**
  - Order Manager's existing T1/T2 handler structure. Add trail logic alongside it, not as a replacement.
  - BacktestEngine's bar processing loop. Add trail/escalation state updates at appropriate points, don't restructure the loop.
  - The existing `enable_trailing_stop` and `trailing_stop_atr_multiplier` fields on `OrderManagerConfig` — these become effectively superseded by the new `ExitManagementConfig`, but removing them risks breaking existing config files. Mark as deprecated in comments, remove in a future cleanup sprint. **At startup, log a WARNING if legacy fields are active (AMD-10):** "Legacy trailing stop config detected (enable_trailing_stop / trailing_stop_atr_multiplier). These fields are deprecated — use config/exit_management.yaml instead. Legacy fields are ignored."

- **Do NOT add:**
  - Trailing stop visualization on the frontend (chart overlay showing trail price over time) — deferred to a future UI sprint.
  - Trail analytics (average trail improvement, trail-vs-fixed comparison) — deferred to Learning Loop V2.
  - Per-trade exit management override via AI Copilot action proposal — deferred.
  - Exit management A/B testing infrastructure — this is Sprint 32.5 (Experiment Registry).

## Interaction Boundaries

- This sprint does NOT change the behavior of:
  - Risk Manager approval/rejection/modification flow
  - Signal generation in any strategy (strategies only add `atr_value` to existing signal emissions)
  - Event Bus subscription patterns
  - IBKR bracket order submission flow (entry + stop + T1 + T2 atomic submission)
  - EOD flatten behavior (unconditional at 15:50 ET)
  - Overflow routing (DEC-375)
  - Reconciliation logic (DEC-369/370)
  - Quality Engine scoring or filtering
  - Catalyst Pipeline
  - Universe Manager routing

- This sprint does NOT affect:
  - Strategies with `trailing_stop.enabled: false` (default) — zero behavioral change
  - Strategies with `escalation.enabled: false` (default) — zero behavioral change
  - Any component that does not read exit management config

## Deferred to Future Sprints

| Item | Target Sprint | Rationale |
|------|--------------|-----------|
| Regime-adaptive exit parameters | Sprint 32+ | Need Learning Loop data first |
| Short selling exit math | Sprint 30 | Short selling infrastructure sprint |
| Trail visualization (chart overlay) | Unscheduled (UI backlog) | Backend-first this sprint |
| Trail analytics (trail-vs-fixed comparison) | Sprint 40 (Learning Loop V2) | Needs significant data accumulation |
| Remove deprecated `enable_trailing_stop`/`trailing_stop_atr_multiplier` from OrderManagerConfig | Next cleanup sprint | Backward compat with existing configs |
| Exit management A/B testing | Sprint 32.5 (Experiment Registry) | Requires experiment infrastructure |
| AI Copilot exit management actions | Unscheduled | Requires tool_use extension |
| `"immediate"` activation + active bracket interaction | Sprint 29+ if needed | Simple passthrough for now; complex interaction deferred |
| Percentage-based `min_trail_distance` | Unscheduled | Fixed-dollar V1 sufficient for current universe (AMD-11) |
