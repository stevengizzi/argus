---BEGIN-REVIEW---

# Sprint 32.9 Session 1 — Tier 2 Review
**Scope:** DEF-139 + DEF-140: EOD Flatten + Startup Zombie Fix (`qty` to `shares` attribute mismatch)

---

## 1. Spec Compliance

### 1a. `qty` to `shares` attribute fix (CRITICAL CHECK)

**PASS.** All four `getattr(pos/bp, "qty", 0)` occurrences reading from broker *position* objects in `order_manager.py` have been changed to `getattr(pos/bp, "shares", 0)`:

| Location | Line (approx) | Status |
|----------|---------------|--------|
| `eod_flatten()` Pass 2 | ~1563 | Fixed |
| `_reconstruct_from_broker()` | ~1708 | Fixed |
| `_reconstruct_known_position()` | ~1886 | Fixed |
| `_check_flatten_pending_timeouts()` error-404 re-query | ~2147 | Fixed |

Additionally, the retry pass in `eod_flatten()` (new code, ~line 1536) correctly uses `getattr(p, "shares", 0)`.

**One intentional non-change confirmed:** Line 1909 reads `getattr(order, "qty", 0)` from a broker *order* object (not a position object). This is correct — broker order objects use `qty`, not `shares`. No remaining `getattr(pos/bp, "qty"` patterns exist for position objects.

**Grep verification:** `getattr(.*"qty"` in order_manager.py returns exactly one hit (line 1909, order object). All position-object reads now use `"shares"`.

### 1b. EOD flatten fill verification (asyncio.Event)

**PASS.** `eod_flatten()` now:
1. Creates `asyncio.Event` per managed symbol before calling `_flatten_position()`
2. Waits via `asyncio.wait_for(asyncio.gather(...), timeout=eod_timeout)`
3. Events are set in two places: `_close_position()` (line ~2486) and `on_cancel()` (line ~615) for flatten orders
4. After timeout, classifies symbols as `filled` or `timed_out`
5. `_eod_flatten_events` dict is cleared after the wait completes (line ~1553)

### 1c. Pass 2 broker-only position discovery

**PASS.** Pass 2 now:
- Runs AFTER Pass 1 verification completes (sequential, not interleaved)
- Uses `getattr(pos, "shares", 0)` (the fix)
- Excludes `managed_symbols` AND `pass1_filled_set` to avoid double-flatten
- Logs count of submitted orders

### 1d. Retry logic

**PASS.** Retry path:
- Gated by `self._config.eod_flatten_retry_rejected`
- Re-queries broker positions via `get_positions()`
- Uses `getattr(p, "shares", 0)` correctly
- Calls `_flatten_unknown_position()` with `force_execute=True`

### 1e. Timeout path cleanup

**PASS.** `_eod_flatten_events` is unconditionally cleared to `{}` on line ~1553, regardless of whether timeout occurred. This prevents stale events from leaking across calls.

### 1f. Startup flatten queue

**PASS.** `_reconstruct_from_broker()` (line ~1708) now reads `shares` attribute. Pre-market zombies will correctly queue with the actual share count rather than defaulting to 0 (which caused silent skip).

### 1g. Mid-session flatten logic unchanged

**PASS.** `_flatten_position()`, `_check_flatten_pending_timeouts()` core retry loop, and `_flatten_pending` semantics are unchanged beyond the `qty`-to-`shares` fix in the error-404 re-query path.

### 1h. Auto-shutdown after verification

**PASS.** `ShutdownRequestedEvent` publishing is now after the post-flatten verification query (line ~1583 verification, then ~1600 shutdown). Previously it was before Pass 2.

### 1i. Config fields

**PASS.** Two new fields on `OrderManagerConfig`:
- `eod_flatten_timeout_seconds: int = Field(default=30, ge=1)`
- `eod_flatten_retry_rejected: bool = True`

Both present in `config/order_manager.yaml` with matching values.

### 1j. Test mock updates

**PASS.** All affected mock broker positions updated from `.qty =` to `.shares =`:
- `test_order_manager.py`: 8 mocks updated
- `test_order_manager_sprint295.py`: 4 mocks updated
- `test_integration_sprint5.py`: 1 mock updated

---

## 2. Test Results

**393 tests passing** in `tests/execution/` + `tests/test_integration_sprint5.py` (0 failures).

New test file `tests/execution/test_order_manager_sprint329.py` adds 13 focused tests covering all spec requirements:
- Reconstruction reads `shares` attribute (2 tests)
- EOD Pass 2 reads `shares` (2 tests)
- Pre-market zombie queuing (1 test)
- Startup queue drain at market open (1 test)
- EOD flatten waits for fills via asyncio.Event (1 test)
- Pass 2 discovers orphans / skips managed (2 tests)
- Retry timed-out positions via broker re-query (1 test)
- Timeout returns cleanly + events cleared (1 test)
- Auto-shutdown fires after verification (1 test)
- Config YAML field validation (1 test)

Test quality is good. Tests use proper async patterns, `asyncio.gather` for concurrent fill delivery, and `asyncio.wait_for` to prevent hangs.

---

## 3. Findings

### F1 (LOW): `main.py` reconciliation path still reads `qty` attribute

`argus/main.py` line ~1400 reads `getattr(pos, "qty", 0)` from broker positions in the reconciliation loop. The close-out report correctly documents this as a deferred item with different semantics. This is **not a regression** introduced by this session — it is pre-existing. However, it is the same root-cause bug pattern (broker Position objects use `shares`, not `qty`). It should be tracked.

### F2 (INFO): Uncommitted changes from other sessions present in working tree

The working tree contains uncommitted changes from what appear to be Sessions 2 and 3 of Sprint 32.9 (main.py signal cutoff, quality engine recalibration, strategy demotions, overflow capacity reduction, experiments enablement, risk limits changes). These are **outside the scope of this review** and do not affect the Session 1 changes, but they explain why the full file-level diff is larger than expected. The Session 1 changes to `order_manager.py`, `config.py` (OrderManagerConfig only), `order_manager.yaml`, and the test files are clean and self-contained.

### F3 (INFO): `config.py` contains Session 2 changes alongside Session 1 changes

The `OrchestratorConfig` additions (`signal_cutoff_enabled`, `signal_cutoff_time`) in `config.py` are from Session 2, not Session 1. Session 1's additions to `OrderManagerConfig` are correct and isolated.

### F4 (LOW): Post-flatten verification may log false CRITICAL

The post-flatten verification (line ~1584) calls `get_positions()` immediately after Pass 2 submits orders. Pass 2 orders may still be in-flight (PENDING status), so the verification query may see positions that are in the process of being sold. The `logger.critical` log could fire spuriously. This is a cosmetic issue — the positions will be sold by the broker — but the CRITICAL log could cause operator alarm. No fill verification is applied to Pass 2 orders (as documented in judgment call #3 in the close-out).

### F5 (LOW): `eod_flatten_events` set on cancel but only for flatten orders

In `on_cancel()`, the EOD event is set only when `pending.order_type == "flatten"`. This is correct behavior — non-flatten cancellations (e.g., cancelled stop or target during bracket teardown) should not signal EOD completion. Verified this is intentional.

---

## 4. Regression Checklist

| Check | Result |
|-------|--------|
| No changes to `argus/strategies/` | PASS |
| No changes to `argus/ui/` | PASS |
| No changes to `argus/api/routes/` | PASS |
| No changes to `argus/data/` | PASS |
| `_flatten_position` core logic unchanged | PASS |
| `_flatten_pending` semantics unchanged | PASS |
| Bracket management unchanged | PASS |
| Line 1909 `getattr(order, "qty")` preserved (order object) | PASS |
| All 393 execution + integration tests pass | PASS |

---

## 5. Close-Out Report Accuracy

The close-out report is accurate and thorough. Self-assessment of CLEAN is appropriate — all spec requirements are met, the deferred item (main.py reconciliation) is properly documented, and all judgment calls are reasonable.

---

## 6. Verdict

All critical checks pass. The `qty` to `shares` fix is applied at every broker-position read site in `order_manager.py`. The EOD flatten flow now waits for fill verification before shutdown. Pass 2 is functional. Tests are comprehensive. No regressions detected.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "confidence": 0.95,
  "findings": [
    {
      "id": "F1",
      "severity": "low",
      "description": "main.py reconciliation path (~line 1400) still reads getattr(pos, 'qty', 0) from broker positions — same root-cause bug pattern. Documented as deferred item in close-out. Pre-existing, not a regression.",
      "file": "argus/main.py",
      "line": 1400
    },
    {
      "id": "F2",
      "severity": "info",
      "description": "Working tree contains uncommitted changes from Sessions 2 and 3. Session 1 changes are self-contained and correct.",
      "file": null,
      "line": null
    },
    {
      "id": "F3",
      "severity": "info",
      "description": "config.py contains OrchestratorConfig additions from Session 2 alongside Session 1 OrderManagerConfig additions.",
      "file": "argus/core/config.py",
      "line": 650
    },
    {
      "id": "F4",
      "severity": "low",
      "description": "Post-flatten verification queries broker immediately after Pass 2 order submission. In-flight orders may cause spurious CRITICAL log. Documented in close-out judgment call #3.",
      "file": "argus/execution/order_manager.py",
      "line": 1584
    }
  ],
  "tests_pass": true,
  "test_count": 393,
  "escalation_triggers": []
}
```
