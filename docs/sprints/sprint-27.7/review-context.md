# Sprint 27.7: Review Context File

> This file is the shared context for all Tier 2 reviews in Sprint 27.7.
> Each session review prompt references this file by path.

---

## Sprint Spec (Summary)

**Goal:** Build the Counterfactual Engine — shadow position tracking for rejected signals, filter accuracy metrics for the Learning Loop, and shadow strategy mode.

**Deliverables:**
1. Shared TheoreticalFillModel extracted from BacktestEngine (stop > target > time_stop > EOD)
2. CounterfactualPosition model (frozen dataclass, 5 exit types, MAE/MFE tracking)
3. CounterfactualTracker (event bus subscriber, candle monitoring, IntradayCandleStore backfill, EOD close, no-data timeout)
4. CounterfactualStore (SQLite in `data/counterfactual.db`, CRUD, retention policy)
5. SignalRejectedEvent (new event type, published from 3 rejection points in `_process_signal()`)
6. CounterfactualConfig (Pydantic model, YAML, config-gated on SystemConfig)
7. FilterAccuracy computation (by stage/reason/grade/regime/strategy, min sample threshold)
8. REST endpoint `GET /api/v1/counterfactual/accuracy` (JWT-protected)
9. Shadow strategy mode (StrategyMode enum, per-strategy config, routing in `_process_signal()`)

**Session Chain:** S1→S2→S3a→S3b→S4→S5 (strict sequential)

**Config Changes:**

| YAML Path | Pydantic Model | Field | Type | Default |
|-----------|---------------|-------|------|---------|
| `counterfactual.enabled` | `CounterfactualConfig` | `enabled` | `bool` | `true` |
| `counterfactual.retention_days` | `CounterfactualConfig` | `retention_days` | `int` | `90` |
| `counterfactual.no_data_timeout_seconds` | `CounterfactualConfig` | `no_data_timeout_seconds` | `int` | `300` |
| `counterfactual.eod_close_time` | `CounterfactualConfig` | `eod_close_time` | `str` | `"16:00"` |
| Per-strategy `mode` | Strategy config model | `mode` | `str` | `"live"` |

---

## Specification by Contradiction (Key Points)

**Do NOT:**
- Modify filter thresholds or quality weights based on counterfactual data (Sprint 28)
- Track strategy-level near-miss events (requires per-strategy changes to all 7 strategies)
- Build counterfactual UI (Sprint 31 Research Console)
- Build shadow vs live comparison tooling (Sprint 32.5)
- Track short-side counterfactual positions
- Stream counterfactual positions via WebSocket
- Track symbols not in the viable universe

**Do NOT modify:**
- `argus/core/risk_manager.py`
- `argus/core/regime.py`
- `argus/analytics/evaluation.py`, `argus/analytics/comparison.py`
- `argus/data/intraday_candle_store.py` (read-only consumer)
- Individual strategy files (`orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `red_to_green.py`, `patterns/bull_flag.py`, `patterns/flat_top_breakout.py`)
- `argus/execution/order_manager.py`
- `argus/ui/` (no frontend changes)

**Edge cases to reject:** Empty target_prices → skip. Zero R → skip. No candle store bars at backfill → skip backfill. System restart with open positions → mark EXPIRED.

---

## Sprint-Level Regression Checklist

- [ ] All existing pytest tests pass (`pytest --ignore=tests/test_main.py` — ~3,412 ± tolerance)
- [ ] All existing Vitest tests pass (~633)
- [ ] **(S1)** BacktestEngine produces identical results after fill model extraction
- [ ] **(S1)** `evaluate_bar_exit()` matches original fill priority for all edge cases
- [ ] **(S3a)** `_process_signal()` for live-mode + counterfactual disabled = identical code path
- [ ] **(S3a)** `_process_signal()` for live-mode + counterfactual enabled = identical order results
- [ ] **(S3b)** Event bus FIFO ordering preserved
- [ ] **(S5)** All existing strategies default to `mode: live`
- [ ] **(S5)** Strategy internal logic unaware of mode
- [ ] **(S2)** Config fields match Pydantic model names exactly
- [ ] **(S2)** CounterfactualStore uses `data/counterfactual.db` (NOT `argus.db`)
- [ ] Do-not-modify files are untouched (see list above)

---

## Sprint-Level Escalation Criteria

**Hard Halts:**
1. BacktestEngine regression after fill model extraction → HALT
2. Fill priority disagreement between shared model and original code → HALT
3. Event bus ordering violation from SignalRejectedEvent publishing → HALT
4. Any pre-existing test failure → HALT
5. `_process_signal()` behavioral change for live-mode strategies → HALT

**Soft Halts:**
6. CounterfactualStore write failures → investigate aiosqlite concurrency
7. IntradayCandleStore backfill returns unexpected data → investigate, may continue with backfill disabled
8. Session compaction warning → log progress, use contingency plans
