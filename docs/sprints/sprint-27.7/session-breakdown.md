# Sprint 27.7: Session Breakdown

## Dependency Chain

```
S1 (model + tracker + fill model)
 └─► S2 (store + config)
      └─► S3 (event wiring + rejection interception + startup)
           └─► S4 (filter accuracy + API + integration tests)
                └─► S5 (shadow strategy mode)
```

All sessions are strictly sequential. No parallelization possible.

---

## Session 1: Core Model + Tracker Logic + Shared Fill Model

**Objective:** Define the CounterfactualPosition lifecycle model, extract the shared TheoreticalFillModel from BacktestEngine, and implement CounterfactualTracker core logic including IntradayCandleStore backfill.

**Creates:**
- `argus/intelligence/counterfactual.py` — RejectionStage enum, CounterfactualPosition dataclass, CounterfactualTracker class (in-memory tracking, candle processing, EOD close, no-data timeout, backfill from IntradayCandleStore)
- `argus/core/fill_model.py` — ExitResult dataclass, ExitReason enum, `evaluate_bar_exit()` function

**Modifies:**
- `argus/backtest/engine.py` — Replace inline fill priority logic in `_process_bar_for_position()` with call to `fill_model.evaluate_bar_exit()`

**Integrates:** N/A (foundational session)

**Parallelizable:** No

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | `counterfactual.py`, `fill_model.py` | 2 × 2 = **4** |
| Files modified | `engine.py` | 1 × 1 = **1** |
| Context reads | `events.py` (SignalEvent, CandleEvent), `regime.py` (RegimeVector), `backtest/engine.py` (fill logic to extract), `intraday_candle_store.py` (API reference) | **4** |
| New tests | ~10 (position lifecycle ×5 exit types, fill model unit ×3, backfill, engine regression) | 10 × 0.5 = **5** |
| Complex integration wiring | No (pure library + surgical engine refactor) | **0** |
| External API debugging | No | **0** |
| Large files (>150 lines) | `counterfactual.py` (~200 lines) | **2** |
| **Total** | | **16** |

⚠️ **Score 16 — High. Must split or reduce.**

Mitigation: The fill model extraction from BacktestEngine is a small, self-contained refactor (~20 lines extracted, ~5 lines of call-site change). The real complexity is in the CounterfactualTracker. I'll keep this as one session because the fill model extraction is prerequisite to testing the tracker's candle processing — splitting would require mocking the fill model in S1 then replacing the mock in a later session, which adds complexity rather than reducing it.

**Revised approach:** Reduce test scope for this session. The BacktestEngine regression test (running a known trade set and comparing results before/after extraction) is critical but counts as 1 test. The fill model unit tests are simple pure-function tests. The position lifecycle tests cover the 5 exit types. That's ~8 tests, not 10.

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | `counterfactual.py`, `fill_model.py` | **4** |
| Files modified | `engine.py` | **1** |
| Context reads | `events.py`, `regime.py`, `engine.py`, `intraday_candle_store.py` | **4** |
| New tests | ~8 | 8 × 0.5 = **4** |
| Large files | `counterfactual.py` | **2** |
| **Total** | | **15** |

Still 15. The honest answer is this session is at the high boundary and the implementer should be aware. The fill model extraction is straightforward — the complexity risk is in the tracker's backfill logic interacting with IntradayCandleStore's API. If backfill proves complex during implementation, it can be deferred to Session 3 as an escalation (backfill is a quality improvement, not a correctness requirement — forward-only monitoring is functional).

**Revised score with backfill deferral contingency:** If backfill is deferred, remove 1 context read (intraday_candle_store.py) and 1 test → **13** (Medium). Implementer should attempt backfill but has an explicit escape hatch.

**Final score: 13–15 (Medium-to-High).** Proceed with caution. Backfill is the pressure valve.

---

## Session 2: CounterfactualStore + Config Layer

**Objective:** Build SQLite persistence for counterfactual positions and the full config layer (Pydantic model, YAML file, SystemConfig wiring).

**Creates:**
- `argus/intelligence/counterfactual_store.py` — CounterfactualStore class (aiosqlite, write on open, update on close, query methods, retention enforcement)
- `config/counterfactual.yaml` — Default configuration

**Modifies:**
- `argus/intelligence/config.py` — Add `CounterfactualConfig` Pydantic model
- `argus/core/config.py` — Add `counterfactual: CounterfactualConfig` field to `SystemConfig`
- `config/system.yaml` — Add `counterfactual` section
- `config/system_live.yaml` — Add `counterfactual` section

**Integrates:** S1's `CounterfactualPosition` (store persists and queries it)

**Parallelizable:** No

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | `counterfactual_store.py`, `counterfactual.yaml` | 2 × 2 = **4** |
| Files modified | `intelligence/config.py`, `core/config.py`, `system.yaml`, `system_live.yaml` | 4 × 1 = **4** |
| Context reads | `counterfactual.py` (S1 output), `telemetry_store.py` (pattern), `intelligence/config.py` (existing models) | **3** |
| New tests | ~8 (store CRUD ×3, retention, config loading ×2, config gating, store query filters) | 8 × 0.5 = **4** |
| Complex integration wiring | No | **0** |
| External API debugging | No | **0** |
| Large files | No | **0** |
| **Total** | | **15** |

⚠️ **Score 15 — High.**

Mitigation: The 4 modified files inflate the score, but `system.yaml` and `system_live.yaml` changes are each 4–6 lines (adding a `counterfactual:` section with `enabled: true`). `core/config.py` is a 2-line addition (import + field). The real work is `counterfactual_store.py` and the Pydantic model in `intelligence/config.py`.

**Reduction option:** Move `system.yaml` + `system_live.yaml` changes to Session 3 (they're needed at startup wiring time, not store creation time). This removes 2 modified files.

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | `counterfactual_store.py`, `counterfactual.yaml` | **4** |
| Files modified | `intelligence/config.py`, `core/config.py` | 2 × 1 = **2** |
| Context reads | `counterfactual.py`, `telemetry_store.py`, `intelligence/config.py` | **3** |
| New tests | ~8 | **4** |
| **Total** | | **13** (Medium) ✅ |

**Final score: 13 (Medium).** Proceed with caution. `system.yaml` / `system_live.yaml` changes deferred to Session 3.

---

## Session 3: SignalRejectedEvent + Rejection Interception + Startup Wiring

**Objective:** Wire the counterfactual system into the running ARGUS process. Add SignalRejectedEvent to the event model, publish from three rejection points in `_process_signal()`, build tracker+store in startup factory, register event bus subscriptions, schedule EOD cleanup task.

**Creates:** None

**Modifies:**
- `argus/core/events.py` — Add `SignalRejectedEvent` dataclass and `RejectionStage` enum (or import from counterfactual.py)
- `argus/main.py` — Publish `SignalRejectedEvent` at 3 rejection points in `_process_signal()`, initialize tracker in startup sequence, register CandleEvent + SignalRejectedEvent subscriptions, schedule EOD cleanup asyncio task
- `argus/intelligence/startup.py` — Factory method `build_counterfactual_tracker()` that creates tracker + store from config
- `config/system.yaml` — Add `counterfactual` section (deferred from S2)
- `config/system_live.yaml` — Add `counterfactual` section (deferred from S2)

**Integrates:** S1 tracker + S2 store + S2 config → wired into main.py signal pipeline and event bus

**Parallelizable:** No

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | None | **0** |
| Files modified | `events.py`, `main.py`, `startup.py`, `system.yaml`, `system_live.yaml` | 5 × 1 = **5** |
| Context reads | `counterfactual.py`, `counterfactual_store.py`, `main.py`, `startup.py` | **4** |
| New tests | ~10 (rejection from quality filter, sizer, risk manager; event bus delivery; candle sub fires; EOD cleanup; config disabled → no interception; no-data timeout; startup creates tracker; startup skips when disabled) | 10 × 0.5 = **5** |
| Complex integration wiring | Yes (main.py + event bus + startup factory + tracker + store) | **3** |
| External API debugging | No | **0** |
| Large files | No | **0** |
| **Total** | | **17** |

⚠️ **Score 17 — High. At the must-split boundary.**

This is the hardest session to decompose because the integration wiring is inherently coupled — you can't test rejection interception without the startup wiring, and you can't test startup wiring without the config in system.yaml.

**Split option:** S3a (events.py + main.py rejection publishing, tested with mock tracker) → S3b (startup.py + system.yaml + candle sub + EOD task, tested end-to-end).

S3a:
| Factor | Points |
|--------|--------|
| Modified: `events.py`, `main.py` | 2 |
| Context reads: `counterfactual.py`, `main.py`, `events.py` | 3 |
| Tests: ~5 | 2.5 |
| Integration wiring (connects to 3 rejection points) | 3 |
| **Total** | **10.5 → 11** (Medium) ✅ |

S3b:
| Factor | Points |
|--------|--------|
| Modified: `startup.py`, `system.yaml`, `system_live.yaml`, `main.py` (startup + subs + EOD) | 4 |
| Context reads: `counterfactual.py`, `counterfactual_store.py`, `startup.py`, `main.py` | 4 |
| Tests: ~5 | 2.5 |
| Integration wiring | 3 |
| **Total** | **13.5 → 13** (Medium) ✅ |

**Decision: Split Session 3 into S3a + S3b.** This brings the sprint to 6 sessions. Both sub-sessions are at 11–13 (Medium).

---

## Session 3a: SignalRejectedEvent + Rejection Publishing

**Objective:** Add SignalRejectedEvent to the event model and publish it from the three rejection points in `_process_signal()`. Test with mock tracker to verify events are published correctly.

**Creates:** None

**Modifies:**
- `argus/core/events.py` — Add `SignalRejectedEvent` dataclass (with signal, rejection_reason, rejection_stage, quality_score, quality_grade, regime_vector fields)
- `argus/main.py` — Publish `SignalRejectedEvent` after each of the 3 rejection points in `_process_signal()`

**Integrates:** N/A (event publishing is standalone; consumers come in S3b)

**Parallelizable:** No

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | None | **0** |
| Files modified | `events.py`, `main.py` | 2 × 1 = **2** |
| Context reads | `counterfactual.py` (RejectionStage enum), `main.py` (current `_process_signal`), `events.py` (existing event patterns) | **3** |
| New tests | ~6 (rejection published from quality filter, sizer, risk manager; event carries correct signal; event not published when counterfactual disabled; no latency regression) | 6 × 0.5 = **3** |
| Complex integration wiring | No (just publishing events, no subscribers wired yet) | **0** |
| **Total** | | **8** (Low) ✅ |

---

## Session 3b: Startup Wiring + Event Subscriptions + EOD Task

**Objective:** Build the counterfactual tracker and store in the startup factory, register event bus subscriptions (SignalRejectedEvent → tracker, CandleEvent → tracker), schedule EOD cleanup task, add counterfactual config to system YAML files.

**Creates:** None

**Modifies:**
- `argus/intelligence/startup.py` — Add `build_counterfactual_tracker()` factory method
- `argus/main.py` — Initialize tracker in startup sequence, register subscriptions, schedule EOD asyncio task
- `config/system.yaml` — Add `counterfactual` section
- `config/system_live.yaml` — Add `counterfactual` section

**Integrates:** S1 tracker + S2 store + S2 config + S3a events → full runtime wiring

**Parallelizable:** No

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | None | **0** |
| Files modified | `startup.py`, `main.py`, `system.yaml`, `system_live.yaml` | 4 × 1 = **4** |
| Context reads | `counterfactual.py`, `counterfactual_store.py`, `startup.py`, `main.py` (post-S3a) | **4** |
| New tests | ~6 (startup creates tracker when enabled, skips when disabled, candle sub delivers to tracker, SignalRejectedEvent sub delivers to tracker, EOD task closes positions, no-data timeout fires) | 6 × 0.5 = **3** |
| Complex integration wiring | Yes (startup → tracker → store → event bus × 2 subs → EOD task) | **3** |
| **Total** | | **14** |

⚠️ **Score 14 — at the boundary.** The integration wiring (+3) is unavoidable — this is the session where everything connects. The 4 modified files include 2 trivial YAML additions.

**Accepted at 14.** This is the integration session — it's expected to be heavy. The implementer should prioritize: (1) startup factory, (2) SignalRejectedEvent subscription, (3) CandleEvent subscription, (4) EOD task, (5) YAML configs. If compaction threatens, YAML configs can be done manually post-session.

---

## Session 4: FilterAccuracy + API Endpoint + Integration Tests

**Objective:** Build filter accuracy computation module, expose via REST endpoint, and write full lifecycle integration tests proving the complete pipeline works end-to-end.

**Creates:**
- `argus/intelligence/filter_accuracy.py` — FilterAccuracyResult dataclass, `compute_filter_accuracy()` function with breakdowns by stage/reason/grade/regime/strategy, minimum sample threshold

**Modifies:**
- `argus/api/routes.py` (or new `argus/api/counterfactual_routes.py`) — `GET /api/v1/counterfactual/accuracy` endpoint

**Integrates:** S1+S2+S3a+S3b → full lifecycle integration tests (rejection → event → tracker → candle monitor → close → store → accuracy query)

**Parallelizable:** No

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | `filter_accuracy.py` | 1 × 2 = **2** |
| Files modified | `routes.py` | 1 × 1 = **1** |
| Context reads | `counterfactual.py`, `counterfactual_store.py`, `main.py` (post-S3b), `routes.py` | **4** |
| New tests | ~10 (accuracy by stage, reason, grade, regime, strategy; min sample threshold; empty data; API endpoint 200/401; full lifecycle integration ×2) | 10 × 0.5 = **5** |
| Complex integration wiring | No (accuracy reads from store, API calls accuracy) | **0** |
| External API debugging | No | **0** |
| Large files | No | **0** |
| **Total** | | **12** (Medium) ✅ |

---

## Session 5: Shadow Strategy Mode

**Objective:** Add StrategyMode enum, per-strategy mode config field, and routing logic in `_process_signal()` that sends shadow-mode signals to the counterfactual tracker instead of the quality/risk pipeline.

**Creates:** None

**Modifies:**
- `argus/strategies/base_strategy.py` — Add `StrategyMode` enum (`LIVE`, `SHADOW`)
- `argus/main.py` — Add shadow-mode routing check at top of `_process_signal()`
- Strategy YAML configs (e.g., `config/strategies/orb_breakout.yaml`) — Add `mode: live` default field

**Integrates:** S1+S3a+S3b tracker → shadow signals routed to counterfactual tracking via `SignalRejectedEvent` with `rejection_stage=SHADOW`

**Parallelizable:** No

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | None | **0** |
| Files modified | `base_strategy.py`, `main.py`, strategy YAML configs (count as 1 — same pattern repeated) | 3 × 1 = **3** |
| Context reads | `counterfactual.py` (RejectionStage), `base_strategy.py`, `main.py` (post-S3b), strategy config models | **4** |
| New tests | ~8 (shadow mode routing, shadow signal tracked counterfactually, live mode unaffected, config parsing, shadow signal carries correct metadata, strategy unaware of mode, default mode is LIVE, StrategyMode enum) | 8 × 0.5 = **4** |
| Complex integration wiring | No (single routing check + config field) | **0** |
| **Total** | | **11** (Medium) ✅ |

---

## Summary

| Session | Scope | Score | Status |
|---------|-------|-------|--------|
| S1 | Core model + tracker + fill model extraction | **13–15** | Medium-to-High (backfill is pressure valve) |
| S2 | Store + config layer | **13** | Medium |
| S3a | SignalRejectedEvent + rejection publishing | **8** | Low |
| S3b | Startup wiring + subscriptions + EOD task | **14** | High (accepted — integration session) |
| S4 | Filter accuracy + API + integration tests | **12** | Medium |
| S5 | Shadow strategy mode | **11** | Medium |

**Total sessions:** 6
**Estimated duration:** ~3 days
**Estimated new tests:** ~48
