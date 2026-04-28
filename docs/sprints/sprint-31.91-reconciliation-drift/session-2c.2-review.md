# Tier 2 Review — Sprint 31.91 Session 2c.2

**Commit:** `24320e5` (phantom-short gate auto-clear, 5-cycle M4 default)
**Reviewer:** Tier 2 backend safety reviewer
**Date:** 2026-04-27 (paper-session-day timezone-anchored)

## Verdict: **CLEAR**

The implementation matches the spec precisely. The only deviation from the spec's pseudocode (J-1) is a structural refactor that collapses two duplicated increment/log/threshold-check branches into a single increment-then-branch-on-log path — observably identical, eliminates a "branches drift apart" risk, and is honestly disclosed in the close-out. All 7 review focus items pass. Pytest baseline target met (5,163 ≥ 5,138).

---

## Tests Run

| Suite | Result |
|---|---|
| `test_session2c2_phantom_short_auto_clear.py` (4 new) | **4 passed** in 0.06s |
| `test_session2c1_phantom_short_gate.py` (Session 2c.1 regression) | **6 passed** in 0.06s |
| `tests/execution/` (full execution layer) | **483 passed** in 7.03s |
| Full pytest baseline (`--ignore=tests/test_main.py -n auto`) | **5,163 passed, 0 failed** in 56.56s |

Pytest delta: +4 tests, exactly matching the close-out claim of `tests_added: 4`. The total `tests_total_after: 5163` claim is verified empirically.

## CI Status

Local-only this run. Nothing observed that would suggest CI divergence:
- All test files are pure-Python; no platform-sensitive paths.
- The new `aiosqlite` interaction in Test 1 uses `tmp_path` (per-test isolated file).
- No new pyarrow/xdist / event-loop closure regressions detected (40 warnings observed are within pre-existing DEF-192 categories).
- Per RULE-050, the operator should still confirm a green CI run on commit `24320e5` before declaring the session done.

---

## Section-by-Section Verdict (Review Focus Items 1–7)

### 1. Default value matches M4 disposition (5 not 3) — **PASS**

`argus/core/config.py:272-283` — `default=5`, `ge=1, le=60`. Field description explicitly cites M4:
> "Default 5 (~5 minutes) per M4 cost-of-error asymmetry: false-clear is more dangerous than false-hold. Was 3 in earlier sprint drafts; raised to 5 during Phase A revisit. Range 1-60 (60 ~hourly cap)."

### 2. Cost-of-error asymmetry rationale documented — **PASS**

Documented in **two** places (spec required at least one):
- Field description at `argus/core/config.py:279-281` (cited above).
- Inline comment on the state field at `argus/execution/order_manager.py:421-423`:
  > "M4 cost-of-error asymmetry: 5 cycles (~5 min) > 3 cycles (~3 min) because false-clear (gate releases while short persists) is more dangerous than false-hold (gate stays engaged a few extra cycles)."

Inline `# Sprint 31.91 Session 2c.2 (D5, M4)` markers also at `argus/core/config.py:267` and `argus/execution/order_manager.py:3999`.

### 3. Counter-reset edge cases — **PASS**

- **Re-detection during partial clear sequence resets cleanly:** `argus/execution/order_manager.py:4019-4030` — the `broker_is_short` branch pops the counter and `continue`s before the increment path. Test 2 (`test_gate_persists_through_transient_broker_zero_resets_counter`) verifies the exact spec sequence: cycle 1 zero (counter=1), cycle 2 SHORT (counter popped), cycles 3..6 zero (counter ramps 1..4), cycle 7 zero (clears).
- **None-safe pop:**
  - Line 4024 `pop(symbol)` is gated by `if symbol in self._phantom_short_clear_cycles:` (line 4023) — safe by construction.
  - Line 4058 `pop(symbol, None)` is None-safe by default argument.
- **Off-by-one:** `current >= clear_threshold` at line 4053. With threshold=5: cycle 4 (`current=4`) does NOT clear; cycle 5 (`current=5`) clears. Verified by Test 1 assertion sequence.

### 4. Snapshot iteration safety — **PASS**

`argus/execution/order_manager.py:4014` — `for symbol in list(self._phantom_short_gated_symbols):`. The clear-path mutation at line 4057 (`discard`) cannot raise `RuntimeError: Set changed size during iteration` because the snapshot is consumed. Inline comment at 4008-4009 documents the intent.

### 5. Persistence on auto-clear — **PASS**

`_remove_gated_symbol_from_db` is invoked at `argus/execution/order_manager.py:4063` via `asyncio.create_task` (fire-and-forget, mirrors Session 2c.1's `_persist_gated_symbol` idiom including `_pending_gate_persist_tasks` tracking and `_log_persist_task_exception` done-callback).

Test 1 (`test_gate_clears_after_5_consecutive_zero_cycles`) verifies the DB row removal end-to-end: pre-persists the row at line 170-172, cycles 1..5, awaits `_pending_gate_persist_tasks` to drain (line 134), then opens a fresh `aiosqlite` connection and asserts `COUNT(*) == 0` for the symbol (lines 137-145).

### 6. No regressions from 2c.1 — **PASS**

All 6 Session 2c.1 tests pass post-2c.2. `_handle_broker_orphan_short` continues to fire from the orphan-loop body at `argus/execution/order_manager.py:3964` BEFORE the new auto-clear loop, so re-detection still triggers the alert and the engagement code path. The auto-clear loop's `broker_is_short` branch resets the clear counter (additive behavior) without touching `_phantom_short_gated_symbols` (gate stays engaged). Idempotency holds.

### 7. "Long shares > 0" branch is intentional — **PASS-WITH-NOTE**

`argus/execution/order_manager.py:4033-4052` — the branch is the `else` arm of `if broker_pos is None`, reached when broker reports a non-short non-None position (i.e., LONG, since SELL was already handled by the `broker_is_short` early-return at line 4019-4030). Inline comment at 4042-4044 documents the rationale: "broker_pos.side == OrderSide.BUY — LONG. Original phantom short has resolved (operator may have flattened then a legitimate long entered, or another path created it)." Confirmed intentional.

**Soft note:** The 4 new tests do not directly exercise the LONG-shares branch (Test 1 uses `{}` empty dict throughout the clear cycles, hitting the `broker_pos is None` path). Behavioral coverage of the LONG branch is structural-equivalent to the zero-shares branch (same increment/threshold semantics, only differs in the log message). Acceptable, but a fifth test exercising LONG-shares clearing could pin this in future. Not a blocker.

---

## Sprint-Level Regression Invariants (5 / 14 / 15)

| # | Invariant | Status |
|---|---|---|
| 5 | Pytest baseline ≥ 5,138 | **PASS** — 5,163 passed, 0 failed |
| 14 | Row "After Session 2c.2" — Recon detects shorts = "full + auto-clear (5-cycle)" | **PASS** — auto-clear logic landed; default threshold = 5 |
| 15 | No scoped exception in 2c.2 | **PASS** — no scoped exception added |

---

## Escalation Triggers

None triggered. Specifically:
- **A2** (Tier 2 CONCERNS or ESCALATE) — verdict is CLEAR.
- **A3** (post-merge paper session abnormality) — not verifiable in this review; flag if observed.
- **B1, B3, B4, B6** — none observed.
- **C7** (existing reconciliation tests fail because auto-clear perturbs cycle-counting) — verified absent: `test_reconciliation.py`, `test_reconciliation_redesign.py`, and the entire `tests/execution/` suite (483 tests) all pass post-2c.2. The `expected_keys` update to `test_reconciliation_config_fields_recognized` is a structural lock-step update mirroring how 2c.1 added `broker_orphan_entry_gate_enabled`.

---

## Do-Not-Modify Verification

Verified no changes to files outside the spec's scope:
- `git diff 6ec03ac..24320e5 -- argus/main.py` returns **empty** (no main.py changes — close-out claim verified).
- All 7 changed files (6 code/test + 1 doc closeout) match the spec's expected `files_modified` list.
- Files modified: `argus/core/config.py`, `argus/execution/order_manager.py`, `config/system.yaml`, `config/system_live.yaml`, `tests/execution/order_manager/test_reconciliation_redesign.py`, `tests/execution/order_manager/test_session2c2_phantom_short_auto_clear.py`, plus `docs/sprints/sprint-31.91-reconciliation-drift/session-2c.2-closeout.md`.

`donotmodify_violations: 0` — verified.

---

## Anchors Cited

| Claim | Anchor |
|---|---|
| `default=5`, M4 in description | `argus/core/config.py:272-283` |
| Inline comment M4 cost-of-error | `argus/execution/order_manager.py:421-423` |
| Snapshot iteration | `argus/execution/order_manager.py:4014` |
| Re-detection reset (None-safe via `if` gate) | `argus/execution/order_manager.py:4019-4030` |
| Single-site increment (J-1 refactor) | `argus/execution/order_manager.py:4031-4032` |
| Threshold check (off-by-one safe) | `argus/execution/order_manager.py:4053` |
| Clear-path None-safe pop | `argus/execution/order_manager.py:4058` |
| Fire-and-forget DB delete | `argus/execution/order_manager.py:4062-4071` |
| AUTO-CLEARED warning log | `argus/execution/order_manager.py:4072-4080` |
| YAML override | `config/system.yaml:70`, `config/system_live.yaml:204` |
| `_remove_gated_symbol_from_db` impl (Session 2c.1 stub) | `argus/execution/order_manager.py:2592-2607` |
| Test 1 DB-row-removed assertion | `tests/execution/order_manager/test_session2c2_phantom_short_auto_clear.py:137-145` |
| Test 2 reset-on-re-detection sequence | `tests/execution/order_manager/test_session2c2_phantom_short_auto_clear.py:180-202` |
| `expected_keys` lock-step update | `tests/execution/order_manager/test_reconciliation_redesign.py:521` |

---

## Final Notes for the Operator

**Soft observations, none blocking:**

1. **J-2 design point — `reset_daily_state` does not clear `_phantom_short_clear_cycles`.** The close-out flags this honestly. Effective behavior: at EOD-without-restart the counter persists; at restart, the in-memory dict is re-created empty in `__init__` (since it's not SQLite-persisted), so counter is implicitly reset on every boot. The gate state itself (the persisted set) survives. This means an EOD-near-clear scenario (e.g., counter=4 going into EOD) would re-accumulate from 0 the next session. That is the safer/more-conservative posture (matches the 2b.1 broker-orphan-long counter, which is also session-scoped and explicitly cleared in `reset_daily_state` at line 3719). Worth noting whether to align: either clear `_phantom_short_clear_cycles` in `reset_daily_state` (making it explicit + symmetric with `_broker_orphan_long_cycles`), or leave as-is and document the asymmetry. Either is defensible; current code is correct as-is per the spec's literal scope.

2. **LONG-shares branch coverage gap.** The 4 new tests exercise `broker_pos is None` (zero-shares) only. The LONG-shares branch is structurally identical (same increment + threshold + log skeleton, different log message), so the gap is small, but a future test (e.g., "operator manually flattens phantom short → strategy fires legitimate long → 5 cycles → gate clears") would lock the LONG path in.

3. **Falsifiable validation pending.** Per Sprint 31.91's structure, the first paper session under OCA-architecture (post-`bf7b869`) is the falsifiable validation surface for the entire Session 0–2d cluster. The auto-clear path will not actually fire until a real phantom-short gate engages and the broker observably returns to non-short. Not Session 2c.2's responsibility, but flagging that the post-merge paper-session debrief is the eventual ground truth for this work.

4. **No new DEFs opened.** Close-out claim verified — none of the soft observations above rise to DEF tier.

---

```json
{
  "session": "2c.2",
  "verdict": "CLEAR",
  "tests_run": {
    "scoped_2c2": "4 passed",
    "scoped_2c1_regression": "6 passed",
    "execution_layer": "483 passed",
    "full_baseline": "5163 passed, 0 failed"
  },
  "pytest_baseline_target": 5138,
  "pytest_baseline_actual": 5163,
  "ci_status": "local-only; no divergence indicators observed",
  "review_focus_items": {
    "1_default_5_m4": "PASS",
    "2_cost_of_error_documented": "PASS",
    "3_counter_reset_edge_cases": "PASS",
    "4_snapshot_iteration_safety": "PASS",
    "5_persistence_on_auto_clear": "PASS",
    "6_no_2c1_regressions": "PASS",
    "7_long_shares_branch_intentional": "PASS-WITH-NOTE"
  },
  "sprint_invariants": {
    "5_pytest_baseline": "PASS",
    "14_recon_detects_shorts_full_plus_autoclear": "PASS",
    "15_no_scoped_exception": "PASS"
  },
  "escalation_triggers_fired": [],
  "donotmodify_violations": 0,
  "soft_concerns": [
    "J-2 design point: _phantom_short_clear_cycles not cleared in reset_daily_state (asymmetric with _broker_orphan_long_cycles which IS cleared) — defensible either way, flagged in close-out",
    "LONG-shares branch (broker_pos.side == OrderSide.BUY) not directly exercised by the 4 new tests; structurally equivalent to zero-shares branch"
  ],
  "new_defs_opened": 0,
  "tier_3_track": "side-aware-reconciliation"
}
```
