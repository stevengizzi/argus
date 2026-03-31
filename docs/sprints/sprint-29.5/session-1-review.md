---BEGIN-REVIEW---

# Sprint 29.5 Session 1 Review: Flatten/Zombie Safety Overhaul

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-31
**Diff:** `git diff HEAD~1` (8 files, +916 / -26 lines)
**Close-out Self-Assessment:** CLEAN

## 1. Spec Compliance

All 6 requirements (R1-R6) from the sprint spec Session 1 scope are implemented:

| Requirement | Status | Notes |
|-------------|--------|-------|
| R1: IBKR error 404 root-cause fix | PASS | `ibkr_broker.py` tracks error 404 symbols; `_check_flatten_pending_timeouts` re-queries broker qty and corrects SELL order quantity |
| R2: Global circuit breaker | PASS | `_flatten_cycle_count` and `_flatten_abandoned` track exhaustion; abandoned symbols skipped in poll loop and `_flatten_position` |
| R3: EOD broker-only positions | PASS | `eod_flatten()` Pass 2 queries `get_positions()`, filters by `managed_symbols`, flattens untracked |
| R4: Startup queue for market open | PASS | `_flatten_unknown_position` gates on market hours via clock, queues pre-market; `_drain_startup_flatten_queue` empties queue at open |
| R5: Time-stop log suppression | PASS | `_suppress_log` flag + `warn_throttled` at 60s interval when flatten pending/abandoned |
| R6: max_flatten_cycles config | PASS | New field on `OrderManagerConfig`, default 2, in `config/order_manager.yaml` |

Test count: 4178 (before) -> 4192 (after). +14 new tests. All 4192 passing.

## 2. Session-Specific Focus Items

### F1: Error 404 detection does NOT interfere with normal SELL order flow
**PASS.** The error 404 handler in `ibkr_broker.py` (line 341) only adds the symbol to `error_404_symbols` set and returns early. This set is only queried in `_check_flatten_pending_timeouts` during retry logic (via `getattr(self._broker, "error_404_symbols", None)`). Normal SELL order submission through `place_order` / `place_bracket_order` is completely unaffected. The set is a passive side-channel, not a gate on order flow.

### F2: Circuit breaker `_flatten_abandoned` cleared by EOD flatten
**PASS.** In `eod_flatten()` (line 1434-1442), `_flatten_abandoned.clear()` and `_flatten_cycle_count.clear()` are called BEFORE the managed-position flatten loop. This means abandoned symbols get a fresh attempt during EOD.

### F3: EOD broker-only flatten does NOT close broker-confirmed positions
**PASS.** Pass 2 at line 1452 computes `managed_symbols = set(self._managed_positions.keys())`. Broker-confirmed positions are tracked IN `_managed_positions` (confirmed via line 908 where `_broker_confirmed[symbol] = True` is set alongside the position being in `_managed_positions`). Therefore, any broker-confirmed position will be in `managed_symbols` and will be filtered OUT of the Pass 2 untracked-position flatten. No overlap.

### F4: Startup queue drain fires only once
**PASS.** The poll loop at line 1303 checks `if self._startup_flatten_queue:` (truthy only when non-empty). `_drain_startup_flatten_queue()` calls `self._startup_flatten_queue.clear()` at line 1679, making subsequent poll iterations skip the drain entirely. No repeated execution.

### F5: `_flatten_unknown_position` correctly queues vs executes
**PASS.** Market hours gate at line 1637: `if not (market_open <= now_et.time() < market_close)` queues to `_startup_flatten_queue`; otherwise executes immediately. Uses `self._clock.now()` for testability. Tests confirm both paths with `FixedClock`.

## 3. Regression Checklist

| # | Invariant | Result |
|---|-----------|--------|
| 1 | Pre-existing pytest tests pass | PASS (4192 passed in 47.71s) |
| 2 | Pre-existing Vitest tests | NOT CHECKED (no frontend changes in this session) |
| 3 | Trailing stop exits unchanged | PASS (no changes to `exit_math.py` or `compute_trail_stop_price`) |
| 4 | Broker-confirmed positions never auto-closed | PASS (`_broker_confirmed` dict unchanged; EOD Pass 2 excludes managed symbols) |
| 5 | Config-gating preserved | PASS (`max_flatten_cycles` has safe default of 2) |
| 6 | EOD flatten triggers shutdown | PASS (`ShutdownRequestedEvent` still published at line 1474) |
| 7 | Quality Engine scoring unchanged | PASS (no modifications) |
| 8 | Catalyst pipeline unchanged | PASS (no `argus/intelligence/` files modified) |
| 9 | CounterfactualTracker unchanged | PASS (no modifications) |
| 10 | Do-not-modify files untouched | PASS (verified: no `intelligence/`, `backtest/`, or `strategies/patterns/` files in diff) |

## 4. Escalation Criteria Check

| # | Criterion | Triggered? |
|---|-----------|-----------|
| 1 | Fill callback beyond error-404 + qty-correction scope | NO — only error 404 handling and qty re-query added |
| 2 | Position close/reconciliation beyond EOD broker-only flatten | NO — reconciliation logic untouched |
| 3 | Trailing stop test regression | NO — no trail tests modified or failing |
| 4 | Do-not-modify files touched | NO — verified clean |
| 5 | New DEC contradicting existing DECs | NO — no new DECs |
| 6 | Test count decrease | NO — increased by 14 |
| 7 | MFE/MAE performance regression | N/A — not in this session's scope |

## 5. Findings

### F1 (LOW): EOD Pass 2 calls `_flatten_unknown_position` which has a market-hours gate
`_flatten_unknown_position` (line 1637) queues instead of executing when called outside 9:30-16:00 ET. EOD flatten is configured at 15:50 ET, safely within the window. However, if `eod_flatten_time` were ever configured after 16:00, Pass 2 flattens would silently queue instead of executing — and there would be no subsequent drain since the system shuts down after EOD. This is a latent configuration trap but not a current-state bug (current config: 15:50 ET).

### F2 (LOW): `_suppress_log` computed after abandoned skip but includes abandoned check
At line 1326, `_suppress_log` checks `symbol in self._flatten_abandoned`, but line 1319 already `continue`s for abandoned symbols. So the `_flatten_abandoned` branch of `_suppress_log` is dead code — it can never be True when execution reaches that line. Harmless but slightly misleading.

### F3 (LOW): `et_tz2` / `now_et2` variable naming
The judgment call to use `et_tz2`/`now_et2` to avoid shadowing is documented and reasonable, but introduces non-obvious naming. A small readability concern, not a correctness issue.

## 6. Test Quality Assessment

14 new tests in `test_order_manager_sprint295.py` covering:
- Error 404 re-query with corrected qty (R1)
- Error 404 position-gone path (R1)
- Circuit breaker single cycle increment (R2)
- Circuit breaker abandonment (R2)
- Abandoned symbol skips flatten (R2)
- EOD clears abandoned set (R2)
- EOD broker-only positions (R3)
- EOD broker query failure (R3)
- Pre-market queue (R4)
- Queue drain (R4)
- Log suppression (R5)
- Config validation (R6, 3 tests)

Spec required >= 12 tests; 14 delivered. Coverage is thorough across all requirements.

## 7. Verdict

All spec requirements implemented. All regression checks pass. No escalation criteria triggered. Three low-severity findings noted (latent config trap, dead-code branch, naming).

---END-REVIEW---

### Post-Review Resolution
| Finding | Status |
|---------|--------|
| F1: EOD Pass 2 market-hours gate | ✅ Fixed — `force_execute=True` bypass |
| F2: Dead-code branch | ✅ Fixed — removed |
| F3: Variable naming | ✅ Comment added |

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "29.5",
  "session": "S1",
  "verdict": "CONCERNS_RESOLVED",
  "post_review_fixes": ["F1", "F2", "F3"],
  "findings": [
    {
      "id": "F1",
      "severity": "LOW",
      "category": "latent-config-trap",
      "summary": "EOD Pass 2 calls _flatten_unknown_position which has a market-hours gate; if eod_flatten_time were configured after 16:00 ET, broker-only flattens would queue and never drain",
      "file": "argus/execution/order_manager.py",
      "line": 1463,
      "recommendation": "Add a comment or consider bypassing the market-hours gate when called from eod_flatten context"
    },
    {
      "id": "F2",
      "severity": "LOW",
      "category": "dead-code",
      "summary": "_suppress_log includes _flatten_abandoned check but abandoned symbols are already skipped by continue on line 1319",
      "file": "argus/execution/order_manager.py",
      "line": 1328,
      "recommendation": "Remove _flatten_abandoned from _suppress_log condition for clarity"
    },
    {
      "id": "F3",
      "severity": "LOW",
      "category": "readability",
      "summary": "et_tz2/now_et2 variable naming to avoid shadowing is non-obvious",
      "file": "argus/execution/order_manager.py",
      "line": 1304,
      "recommendation": "Consider extracting ET time conversion to a helper method"
    }
  ],
  "tests": {
    "total": 4192,
    "passed": 4192,
    "failed": 0,
    "new": 14
  },
  "escalation_triggers": [],
  "regression_check": "PASS",
  "do_not_modify_check": "PASS",
  "close_out_accuracy": "ACCURATE"
}
```
