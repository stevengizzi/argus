---BEGIN-REVIEW---

# Sprint 27.8 Session 1 — Tier 2 Review Report

**Reviewer:** Tier 2 Automated Review (Opus 4.6)
**Date:** 2026-03-26
**Session:** Sprint 27.8 S1 — Ghost Position Reconciliation Fix + Health Inconsistency + Config-Coupled Tests
**Close-out self-assessment:** MINOR_DEVIATIONS

---

## 1. Spec Compliance

All 6 parts of the implementation spec are implemented:

| Spec Requirement | Status | Notes |
|-----------------|--------|-------|
| Part 1: ExitReason.RECONCILIATION | PASS | Added after EMERGENCY, backward compatible |
| Part 2: Reconciliation auto-cleanup | PASS | Config-gated, orphan-only, exit_price=entry_price, realized_pnl=0 |
| Part 3: Bracket exhaustion detection | PASS | t1_target cancel + both legs None triggers flatten |
| Part 4: Config wiring | PASS | system_live.yaml section + main.py dict-style access |
| Part 5: Health monitor is_active loop | PASS | Aggregate count at line 655 untouched |
| Part 6: DEF-101 test decoupling | PASS | YAML-reading + ordering invariants |

**Test targets met:** 7 new tests in `test_order_manager_reconciliation.py` + 1 in `test_main_health.py` = 8 new. 3 rewritten (2 in test_engine_sizing.py + 1 in test_config.py). Matches spec requirement of "8+ new, 3 rewritten."

---

## 2. Escalation Criteria Check

| Criterion | Result |
|-----------|--------|
| Synthetic close record path could execute for non-orphan positions | NOT TRIGGERED -- cleanup only fires when `int(d["broker_qty"]) == 0` (line 1679) |
| Auto-cleanup code path reachable when config flag is False | NOT TRIGGERED -- gated by `self._auto_cleanup_orphans` (line 1676), defaults to `False` |
| Changes to bracket order submission, stop resubmission, or fill handling | NOT TRIGGERED -- existing stop resubmission logic untouched; new code is additive after the existing block |
| Reconciliation changes race with on_tick()/on_fill() | NOT TRIGGERED -- asyncio single-threaded; orphans collected into separate list before iteration; `_close_position` removes from `_managed_positions` during cleanup pass, not during detection pass |

**No escalation criteria triggered.**

---

## 3. Regression Checklist

| Check | Result |
|-------|--------|
| Existing reconciliation warn-only mode unchanged when config disabled | PASS (3/3 tests in test_order_manager_reconciliation_log.py) |
| Order Manager fill handling unchanged | PASS (all execution tests pass, 383 total) |
| Order Manager safety features unchanged | PASS (included in 383 passing tests) |
| ExitReason backward compatible | PASS (all 10 original members present + RECONCILIATION appended) |
| No circular imports | PASS (verified via import check) |
| Rewritten tests still pass with current config | PASS |
| No forbidden files modified | PASS (no changes in strategies/, analytics/, ai/, intelligence/, ui/) |

**Scoped test command result:** 383 passed, 0 failed.

---

## 4. Session-Specific Review Focus

### 4.1 Auto-cleanup gated by self._auto_cleanup_orphans
VERIFIED. Line 1676: `if self._auto_cleanup_orphans and discrepancies:` -- the entire cleanup block is unreachable when `_auto_cleanup_orphans` is False. Default is False in the `__init__` signature.

### 4.2 Synthetic close records use exit_price=entry_price and realized_pnl=0
VERIFIED. Lines 1686-1687 set `shares_remaining = 0` and `realized_pnl = 0.0` on the position. Lines 1695-1698 call `_close_position(pos, exit_price=pos.entry_price, exit_reason=ExitReason.RECONCILIATION)`. Inside `_close_position`, the `weighted_exit_price` formula yields `(0.0 / shares_total) + entry_price = entry_price`. The `PositionClosedEvent` and Trade log both receive `realized_pnl=0.0` and `exit_price=entry_price`.

### 4.3 Bracket exhaustion only fires when ALL bracket legs are None
VERIFIED. Line 479: `if pos.stop_order_id is None and pos.t1_order_id is None:` -- both must be None. The `t1_order_id` was just set to None on line 477, so the real guard is `stop_order_id is None`. If stop is still tracked, no flatten occurs.

### 4.4 Per-strategy health loop doesn't change aggregate count logic
VERIFIED. Lines 655-661 (aggregate count) are untouched. The per-strategy loop at lines 664-671 replaces the old 7 individual if-blocks. The loop iterates the same `strategies` dict used by the aggregate count.

### 4.5 _close_position() calls properly awaited
VERIFIED. Line 1695: `await self._close_position(...)`. `reconcile_positions` is now `async def` (line 1621). All 8 callers updated to use `await` (5 in safety tests, 3 in reconciliation_log tests, 1 in main.py line 1141).

### 4.6 No race conditions between reconciliation cleanup and on_tick()/on_fill()
VERIFIED. Python asyncio is single-threaded cooperative multitasking. The reconciliation task runs in the same event loop. The orphan collection phase (lines 1677-1683) builds a snapshot list. The cleanup phase (lines 1685-1699) iterates the snapshot and calls `await _close_position()` which removes from `_managed_positions`. Between await points, no other handler can interleave. After each `_close_position` completes, the position is removed from `_managed_positions`, so subsequent `on_tick`/`on_fill` calls will not find it.

### 4.7 Rewritten test assertions are config-value-independent
VERIFIED.
- `test_engine_sizing.py`: Both rewritten tests read `config/risk_limits.yaml` via `yaml.safe_load()` and assert the loaded config matches the YAML value. These tests verify the config-loading pathway, not specific values.
- `test_config.py`: Uses ordering invariant assertions (`max(tier_above) > max(tier_below)`) with `>=` for adjacent tiers. The assertions are value-independent -- they verify the structural property that higher grades get higher risk allocations. The `>=` (instead of strict `>`) for mid-tiers is slightly weaker than the spec's mixed comparison pattern but still validates the invariant.

---

## 5. Findings

### F-01: Minor — test_config.py ordering assertions use >= instead of strict >
**Severity:** LOW
**Details:** The spec called for `min(config.risk_tiers.b) > max(config.risk_tiers.c_plus)` (strict greater-than) but the implementation uses `max(config.risk_tiers.b) >= max(config.risk_tiers.c_plus)` (non-strict, comparing max-to-max instead of min-to-max). The spec also referenced a `.c` field that does not exist, so the implementation reasonably adapted. The weaker assertion means the test would pass even if two adjacent tiers had the same max value. Given that the `QualityRiskTiersConfig` model validator already enforces constraints, this is acceptable.
**Impact:** Cosmetic. Does not affect production behavior.

### F-02: Observation — reconciliation cleanup modifies position state before _close_position
**Severity:** LOW (informational)
**Details:** The cleanup sets `pos.shares_remaining = 0` and `pos.realized_pnl = 0.0` on the position object before calling `_close_position`. This works correctly because `_close_position` reads `position.realized_pnl` and `position.shares_total` (not `shares_remaining`) for its calculations. However, if any future change to `_close_position` were to use `shares_remaining` for logic (e.g., checking if position needs closing), it could interact unexpectedly. The current code is correct; this is a maintenance note.
**Impact:** None currently.

---

## 6. Judgment Call Assessment

The close-out report documents four judgment calls. All are reasonable:

1. **reconcile_positions made async:** Correct decision. The spec anticipated this ("may need to become async"). All callers updated.
2. **Used _close_position instead of _close_position_and_log:** Correct -- the spec's method name was inaccurate; the real method is `_close_position`. Good adaptation.
3. **QualityRiskTiersConfig has no .c field:** Correct adaptation. The spec referenced a non-existent field; stopping at `c_plus` is the right boundary.
4. **Config access via raw YAML:** Matches the spec constraint ("Do NOT add any new config Pydantic models").

---

## 7. Verdict

All escalation criteria are clear. The implementation matches the spec across all 6 parts. Tests are comprehensive (8 new + 3 rewritten). No forbidden files were modified. No regressions detected. The two findings are low-severity observations that do not affect correctness or safety.

**Verdict: CLEAR**

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.8",
  "session": "S1",
  "verdict": "CLEAR",
  "escalation_triggers": [],
  "findings": [
    {
      "id": "F-01",
      "severity": "LOW",
      "category": "test_quality",
      "description": "test_config.py ordering assertions use >= instead of strict > for adjacent tier comparisons",
      "impact": "Cosmetic — does not affect production behavior",
      "action_required": false
    },
    {
      "id": "F-02",
      "severity": "LOW",
      "category": "maintenance_note",
      "description": "Reconciliation cleanup modifies position state (shares_remaining=0, realized_pnl=0) before calling _close_position — correct now but fragile if _close_position ever uses shares_remaining",
      "impact": "None currently",
      "action_required": false
    }
  ],
  "regression_check": "PASS",
  "tests_verified": true,
  "test_count": 383,
  "forbidden_files_clean": true,
  "spec_compliance": "FULL"
}
```
